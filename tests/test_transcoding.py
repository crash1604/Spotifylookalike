"""
Tests for the audio transcoding module.

Covers:
- transcoding.service: check_ffmpeg_installed, transcode, probe_audio, generate_waveform
- transcoding.tasks: transcode_track (execution, idempotency, status transitions, fan-out)
- transcoding.tasks: generate_waveform_task, probe_and_update_metadata
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch, call

from tests.factories import TrackFactory, TranscodedTrackFactory


# =============================================================================
# Service Layer Unit Tests (subprocess mocked)
# =============================================================================

class TestCheckFfmpegInstalled:
    """Tests for the check_ffmpeg_installed() helper."""

    def test_returns_true_when_ffmpeg_present(self):
        from transcoding.service import check_ffmpeg_installed
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch('transcoding.service.subprocess.run', return_value=mock_result):
            assert check_ffmpeg_installed() is True

    def test_returns_false_when_ffmpeg_missing(self):
        from transcoding.service import check_ffmpeg_installed
        with patch('transcoding.service.subprocess.run', side_effect=FileNotFoundError):
            assert check_ffmpeg_installed() is False

    def test_returns_false_on_nonzero_exit(self):
        from transcoding.service import check_ffmpeg_installed
        import subprocess
        with patch(
            'transcoding.service.subprocess.run',
            side_effect=subprocess.CalledProcessError(1, 'ffmpeg'),
        ):
            assert check_ffmpeg_installed() is False


class TestProbeAudio:
    """Tests for probe_audio() which wraps ffprobe."""

    def _make_ffprobe_result(self, duration='210.5', bitrate='320000', sample_rate='44100'):
        data = {
            'format': {
                'duration': duration,
                'bit_rate': bitrate,
                'size': '8400000',
                'format_name': 'mp3',
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'mp3',
                'sample_rate': sample_rate,
                'channels': 2,
                'bit_rate': bitrate,
            }],
        }
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = json.dumps(data)
        mock.stderr = ''
        return mock

    def test_returns_duration(self):
        from transcoding.service import probe_audio
        with patch('transcoding.service.subprocess.run', return_value=self._make_ffprobe_result()):
            result = probe_audio('/fake/path.mp3')
        assert result['duration'] == pytest.approx(210.5)

    def test_returns_bitrate_in_kbps(self):
        from transcoding.service import probe_audio
        with patch('transcoding.service.subprocess.run', return_value=self._make_ffprobe_result(bitrate='320000')):
            result = probe_audio('/fake/path.mp3')
        assert result['bitrate'] == 320  # 320000 / 1000

    def test_returns_sample_rate(self):
        from transcoding.service import probe_audio
        with patch('transcoding.service.subprocess.run', return_value=self._make_ffprobe_result(sample_rate='48000')):
            result = probe_audio('/fake/path.mp3')
        assert result['sample_rate'] == 48000

    def test_raises_when_ffprobe_missing(self):
        from transcoding.service import probe_audio, FFmpegNotFoundError
        with patch('transcoding.service.subprocess.run', side_effect=FileNotFoundError):
            with pytest.raises(FFmpegNotFoundError):
                probe_audio('/fake/path.mp3')


class TestTranscodeService:
    """Tests for the transcode() function."""

    def test_raises_for_nonexistent_input(self, tmp_path):
        from transcoding.service import transcode, TranscodingError
        with pytest.raises(TranscodingError, match='does not exist'):
            transcode('/nonexistent/file.mp3', str(tmp_path / 'out.mp3'))

    def test_raises_for_unsupported_codec(self, tmp_path):
        from transcoding.service import transcode, TranscodingError
        # Create a fake input file so it passes the existence check
        src = tmp_path / 'input.mp3'
        src.write_bytes(b'\xff\xfb\x90\x00')
        with pytest.raises(TranscodingError, match='Unsupported codec'):
            transcode(str(src), str(tmp_path / 'out.xyz'), codec='xyz123')

    def test_calls_ffmpeg_with_correct_args(self, tmp_path):
        from transcoding.service import transcode
        src = tmp_path / 'input.mp3'
        src.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 100)
        out = str(tmp_path / 'out.mp3')

        # Also create the output file so transcode() doesn't raise "Output file was not created"
        def fake_run(cmd, **kwargs):
            output_path = cmd[-1]
            with open(output_path, 'wb') as f:
                f.write(b'\xff\xfb\x90\x00')
            result = MagicMock()
            result.returncode = 0
            return result

        with patch('transcoding.service.subprocess.run', side_effect=fake_run) as mock_run:
            result_path = transcode(str(src), out, codec='mp3', bitrate=160)

        mock_run.assert_called_once()
        cmd_args = mock_run.call_args[0][0]
        assert 'ffmpeg' in cmd_args[0]
        assert '-b:a' in cmd_args
        assert '160k' in cmd_args

    def test_ffmpeg_failure_raises_transcoding_error(self, tmp_path):
        from transcoding.service import transcode, TranscodingError
        import subprocess as sp
        src = tmp_path / 'input.mp3'
        src.write_bytes(b'\xff\xfb\x90\x00')

        with patch(
            'transcoding.service.subprocess.run',
            side_effect=sp.CalledProcessError(1, 'ffmpeg', stderr='error'),
        ):
            with pytest.raises(TranscodingError):
                transcode(str(src), str(tmp_path / 'out.mp3'))


# =============================================================================
# Celery Task Tests (DB + mocked subprocess)
# =============================================================================

@pytest.mark.django_db
class TestTranscodeTrackTask:
    """Tests for the transcode_track Celery task."""

    @pytest.fixture
    def track_with_file(self, tmp_path, settings):
        """Create a Track whose audio_file actually exists on disk."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio = tmp_path / 'test.mp3'
        audio.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 200)
        track = TrackFactory()
        track.audio_file.save('task_test.mp3', open(str(audio), 'rb'), save=True)
        return track

    def _mock_transcode(self, tmp_path):
        """Return a patch context that makes transcode() create a fake output file."""
        def fake_transcode(input_path, output_path, **kwargs):
            # Ensure the output directory exists and create the output file
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path + '.mp3', 'wb') as f:
                f.write(b'\xff\xfb\x90\x00')
            return output_path + '.mp3'
        return patch('transcoding.tasks.transcode', side_effect=fake_transcode)

    def test_task_creates_transcoded_track(self, track_with_file, tmp_path, settings):
        """Task creates a TranscodedTrack row with status=completed."""
        from transcoding.tasks import transcode_track
        from transcoding.models import TranscodedTrack

        with self._mock_transcode(tmp_path):
            result = transcode_track(track_with_file.id, quality='medium')

        assert result['status'] == 'completed'
        assert TranscodedTrack.objects.filter(
            original_track=track_with_file, quality='medium'
        ).exists()

    def test_task_sets_status_completed(self, track_with_file, tmp_path, settings):
        """TranscodedTrack status transitions pending → processing → completed."""
        from transcoding.tasks import transcode_track
        from transcoding.models import TranscodedTrack

        with self._mock_transcode(tmp_path):
            transcode_track(track_with_file.id, quality='medium')

        tt = TranscodedTrack.objects.get(original_track=track_with_file, quality='medium')
        assert tt.status == 'completed'

    def test_task_is_idempotent_for_completed_track(self, track_with_file, tmp_path, settings):
        """Re-running the task for an already-completed TranscodedTrack returns 'skipped'."""
        from transcoding.tasks import transcode_track
        from transcoding.models import TranscodedTrack

        # Pre-create a completed record
        tt = TranscodedTrackFactory(
            original_track=track_with_file,
            quality='medium',
            status='completed',
        )
        # Ensure it has a file (ContentFile already saved by factory)

        with patch('transcoding.tasks.transcode') as mock_transcode:
            result = transcode_track(track_with_file.id, quality='medium')

        mock_transcode.assert_not_called()
        assert result['status'] == 'skipped'

    def test_task_returns_error_for_nonexistent_track(self, db):
        """Nonexistent track_id returns error status without raising."""
        from transcoding.tasks import transcode_track
        result = transcode_track(99999, quality='medium')
        assert result['status'] == 'error'
        assert 'not found' in result['detail']

    def test_task_sets_status_failed_on_transcode_error(self, track_with_file, tmp_path, settings):
        """If transcode() raises TranscodingError, status is set to failed."""
        from transcoding.tasks import transcode_track
        from transcoding.models import TranscodedTrack
        from transcoding.service import TranscodingError

        with patch('transcoding.tasks.transcode', side_effect=TranscodingError('boom')):
            with pytest.raises(TranscodingError):
                transcode_track(track_with_file.id, quality='medium')

        tt = TranscodedTrack.objects.get(original_track=track_with_file, quality='medium')
        assert tt.status == 'failed'
        assert 'boom' in tt.error_message

    def test_task_returns_error_for_unknown_quality(self, track_with_file, db):
        """Unknown quality preset returns error dict (not exception)."""
        from transcoding.tasks import transcode_track
        result = transcode_track(track_with_file.id, quality='ultra_lossless')
        assert result['status'] == 'error'


@pytest.mark.django_db
class TestTranscodeAllQualitiesTask:
    """Tests for the transcode_all_qualities fan-out task."""

    def test_dispatches_task_for_each_preset(self, db, settings):
        """transcode_all_qualities dispatches one transcode_track task per preset."""
        from transcoding.tasks import transcode_all_qualities

        settings.STREAMING_QUALITY_PRESETS = {
            'low': {'bitrate': 96, 'format': 'mp3'},
            'medium': {'bitrate': 160, 'format': 'mp3'},
        }

        with patch('transcoding.tasks.transcode_track') as mock_task:
            mock_task.delay = MagicMock()
            result = transcode_all_qualities(42)

        assert mock_task.delay.call_count == 2
        called_qualities = {c.args[1] for c in mock_task.delay.call_args_list}
        assert called_qualities == {'low', 'medium'}
        assert result['status'] == 'dispatched'


@pytest.mark.django_db
class TestGenerateWaveformTask:
    """Tests for the generate_waveform_task Celery task."""

    def test_generates_and_saves_waveform(self, tmp_path, settings):
        """Task calls generate_waveform and saves data to the track."""
        settings.MEDIA_ROOT = str(tmp_path)
        audio = tmp_path / 'wave.mp3'
        audio.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 200)

        track = TrackFactory()
        track.audio_file.save('wave_test.mp3', open(str(audio), 'rb'), save=True)
        track.waveform_data = None
        track.save()

        fake_waveform = [0.5] * 200

        with patch('transcoding.tasks.generate_waveform', return_value=fake_waveform):
            from transcoding.tasks import generate_waveform_task
            result = generate_waveform_task(track.id, num_points=200)

        assert result['status'] == 'completed'
        assert result['points'] == 200
        track.refresh_from_db()
        assert track.waveform_data == fake_waveform

    def test_returns_error_for_missing_track(self, db):
        from transcoding.tasks import generate_waveform_task
        result = generate_waveform_task(99999)
        assert result['status'] == 'error'
