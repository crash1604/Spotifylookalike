"""
FFmpeg transcoding service.

Wraps FFmpeg CLI to convert audio files between formats and bitrates
for adaptive-bitrate streaming.

Requires FFmpeg to be installed on the system:
    apt-get install ffmpeg   (Debian/Ubuntu)
    brew install ffmpeg      (macOS)
"""

import os
import subprocess
import logging
import json
import tempfile
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger('transcoding')


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg binary is not available."""


class TranscodingError(Exception):
    """Raised when a transcoding operation fails."""


def _ffmpeg_bin() -> str:
    """Return the path to the ffmpeg binary."""
    return getattr(settings, 'FFMPEG_BINARY', 'ffmpeg')


def _ffprobe_bin() -> str:
    """Return the path to the ffprobe binary."""
    return getattr(settings, 'FFPROBE_BINARY', 'ffprobe')


def check_ffmpeg_installed() -> bool:
    """Return True if ffmpeg is reachable."""
    try:
        subprocess.run(
            [_ffmpeg_bin(), '-version'],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def probe_audio(input_path: str) -> dict:
    """
    Use ffprobe to extract metadata from an audio file.

    Returns a dict with keys like:
        duration, bitrate, sample_rate, channels, codec, format_name
    """
    cmd = [
        _ffprobe_bin(),
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_path,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30,
        )
    except FileNotFoundError:
        raise FFmpegNotFoundError('ffprobe is not installed or not on PATH.')
    except subprocess.CalledProcessError as exc:
        raise TranscodingError(f'ffprobe failed: {exc.stderr}')

    data = json.loads(result.stdout)
    fmt = data.get('format', {})

    audio_stream = None
    for s in data.get('streams', []):
        if s.get('codec_type') == 'audio':
            audio_stream = s
            break

    return {
        'duration': float(fmt.get('duration', 0)),
        'bitrate': int(fmt.get('bit_rate', 0)) // 1000,  # kbps
        'sample_rate': int(audio_stream['sample_rate']) if audio_stream else 44100,
        'channels': int(audio_stream.get('channels', 2)) if audio_stream else 2,
        'codec': audio_stream.get('codec_name', 'unknown') if audio_stream else 'unknown',
        'format_name': fmt.get('format_name', 'unknown'),
    }


def transcode(
    input_path: str,
    output_path: str,
    codec: str = 'mp3',
    bitrate: Optional[int] = None,
    sample_rate: int = 44100,
    channels: int = 2,
) -> str:
    """
    Transcode an audio file using FFmpeg.

    Args:
        input_path:  Path to the source audio file.
        output_path: Desired path for the output file.
        codec:       Target codec – mp3, aac, flac, opus, vorbis.
        bitrate:     Target bitrate in kbps (ignored for lossless codecs).
        sample_rate: Output sample rate in Hz.
        channels:    Number of output audio channels.

    Returns:
        The absolute path of the transcoded file.

    Raises:
        FFmpegNotFoundError: If ffmpeg is missing.
        TranscodingError:    If the conversion fails.
    """
    if not os.path.isfile(input_path):
        raise TranscodingError(f'Source file does not exist: {input_path}')

    codec_map = {
        'mp3': 'libmp3lame',
        'aac': 'aac',
        'flac': 'flac',
        'opus': 'libopus',
        'vorbis': 'libvorbis',
        'wav': 'pcm_s16le',
    }

    ext_map = {
        'mp3': '.mp3',
        'aac': '.m4a',
        'flac': '.flac',
        'opus': '.opus',
        'vorbis': '.ogg',
        'wav': '.wav',
    }

    ffmpeg_codec = codec_map.get(codec)
    if ffmpeg_codec is None:
        raise TranscodingError(f'Unsupported codec: {codec}')

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Make sure the output extension matches the codec
    stem = Path(output_path).stem
    output_path = str(Path(output_path).parent / f'{stem}{ext_map[codec]}')

    cmd = [
        _ffmpeg_bin(),
        '-y',              # overwrite without asking
        '-i', input_path,
        '-vn',             # drop video stream
        '-acodec', ffmpeg_codec,
        '-ar', str(sample_rate),
        '-ac', str(channels),
    ]

    # Add bitrate flag only for lossy codecs
    if bitrate and codec not in ('flac', 'wav'):
        cmd += ['-b:a', f'{bitrate}k']

    cmd.append(output_path)

    logger.info('Running FFmpeg: %s', ' '.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10-minute safety net
        )
    except FileNotFoundError:
        raise FFmpegNotFoundError('ffmpeg is not installed or not on PATH.')
    except subprocess.CalledProcessError as exc:
        raise TranscodingError(
            f'FFmpeg failed (exit {exc.returncode}): {exc.stderr[:500]}'
        )
    except subprocess.TimeoutExpired:
        raise TranscodingError('FFmpeg timed out after 10 minutes.')

    if not os.path.isfile(output_path):
        raise TranscodingError('Output file was not created by FFmpeg.')

    logger.info('Transcoding complete: %s → %s', input_path, output_path)
    return output_path


def generate_waveform(input_path: str, num_points: int = 200) -> list[float]:
    """
    Generate waveform amplitude data from an audio file using FFmpeg.

    Returns a list of *num_points* normalised amplitude values (0.0-1.0)
    suitable for rendering a waveform visualisation on the client.
    """
    cmd = [
        _ffmpeg_bin(),
        '-i', input_path,
        '-ac', '1',                 # mono
        '-filter:a', f'aresample=8000,astats=metadata=1:reset=1',
        '-f', 'null', '-',
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    # Fallback: produce a simple peak-per-chunk waveform via raw PCM
    with tempfile.NamedTemporaryFile(suffix='.raw', delete=True) as tmp:
        pcm_cmd = [
            _ffmpeg_bin(),
            '-y', '-i', input_path,
            '-ac', '1',
            '-ar', '8000',
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            tmp.name,
        ]
        try:
            subprocess.run(pcm_cmd, capture_output=True, check=True, timeout=120)
        except Exception:
            return []

        raw = Path(tmp.name).read_bytes()

    if len(raw) < 2:
        return []

    import struct
    samples = struct.unpack(f'<{len(raw) // 2}h', raw)
    chunk_size = max(1, len(samples) // num_points)

    peaks: list[float] = []
    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        peak = max(abs(s) for s in chunk) if chunk else 0
        peaks.append(peak / 32768.0)

    # Trim or pad to exact length
    peaks = peaks[:num_points]
    while len(peaks) < num_points:
        peaks.append(0.0)

    return peaks
