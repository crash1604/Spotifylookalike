"""
Celery tasks for background audio transcoding.
"""

import os
import logging
from django.conf import settings
from django.utils import timezone
from django.core.files import File
from celery import shared_task

logger = logging.getLogger('transcoding')


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={'max_retries': 3},
    name='transcoding.transcode_track',
)
def transcode_track(self, track_id: int, quality: str = 'medium'):
    """
    Transcode a track to the requested quality preset.

    This task is idempotent – if a TranscodedTrack for the given
    (track, quality) pair already exists and is completed it returns early.
    """
    from music.models import Track
    from transcoding.models import TranscodedTrack
    from transcoding.service import transcode, probe_audio, TranscodingError

    presets = getattr(settings, 'STREAMING_QUALITY_PRESETS', {})
    preset = presets.get(quality)
    if preset is None:
        logger.error('Unknown quality preset: %s', quality)
        return {'status': 'error', 'detail': f'Unknown preset: {quality}'}

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        logger.error('Track %s does not exist', track_id)
        return {'status': 'error', 'detail': 'Track not found'}

    if not track.audio_file:
        return {'status': 'error', 'detail': 'Track has no audio file'}

    # Get or create the TranscodedTrack row
    transcoded, created = TranscodedTrack.objects.get_or_create(
        original_track=track,
        quality=quality,
        defaults={
            'codec': preset['format'],
            'bitrate': preset.get('bitrate'),
            'status': 'pending',
        },
    )

    if not created and transcoded.status == 'completed' and transcoded.file:
        logger.info('Track %s already transcoded at %s', track_id, quality)
        return {'status': 'skipped', 'detail': 'Already transcoded'}

    # Mark as processing
    transcoded.status = 'processing'
    transcoded.error_message = ''
    transcoded.save(update_fields=['status', 'error_message'])

    input_path = track.audio_file.path
    output_dir = os.path.join(settings.MEDIA_ROOT, 'transcoded')
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f'track_{track_id}_{quality}'
    output_path = os.path.join(output_dir, output_filename)

    try:
        result_path = transcode(
            input_path=input_path,
            output_path=output_path,
            codec=preset['format'],
            bitrate=preset.get('bitrate'),
        )

        file_size = os.path.getsize(result_path)
        with open(result_path, 'rb') as f:
            transcoded.file.save(
                os.path.basename(result_path),
                File(f),
                save=False,
            )
        transcoded.file_size = file_size
        transcoded.status = 'completed'
        transcoded.completed_at = timezone.now()
        transcoded.save()

        # Clean up the temp file since Django copied it into MEDIA_ROOT
        if os.path.isfile(result_path) and result_path != transcoded.file.path:
            os.remove(result_path)

        logger.info(
            'Transcoded track %s to %s (%d bytes)',
            track_id, quality, file_size,
        )
        return {'status': 'completed', 'file_size': file_size}

    except TranscodingError as exc:
        transcoded.status = 'failed'
        transcoded.error_message = str(exc)
        transcoded.save(update_fields=['status', 'error_message'])
        logger.error('Transcoding failed for track %s: %s', track_id, exc)
        raise  # Let Celery retry


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    name='transcoding.transcode_all_qualities',
)
def transcode_all_qualities(self, track_id: int):
    """
    Fan-out task that triggers transcoding for every quality preset.
    """
    presets = getattr(settings, 'STREAMING_QUALITY_PRESETS', {})
    for quality in presets:
        transcode_track.delay(track_id, quality)
    return {'status': 'dispatched', 'qualities': list(presets.keys())}


@shared_task(name='transcoding.generate_waveform_task')
def generate_waveform_task(track_id: int, num_points: int = 200):
    """
    Generate and persist waveform data for a track.
    """
    from music.models import Track
    from transcoding.service import generate_waveform

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return {'status': 'error', 'detail': 'Track not found'}

    if not track.audio_file:
        return {'status': 'error', 'detail': 'No audio file'}

    waveform = generate_waveform(track.audio_file.path, num_points)
    if waveform:
        track.waveform_data = waveform
        track.save(update_fields=['waveform_data'])
        return {'status': 'completed', 'points': len(waveform)}

    return {'status': 'failed', 'detail': 'Waveform generation returned empty'}


@shared_task(name='transcoding.probe_and_update_metadata')
def probe_and_update_metadata(track_id: int):
    """
    Read audio metadata via ffprobe and store it on the Track model.
    """
    from music.models import Track
    from transcoding.service import probe_audio

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return

    if not track.audio_file:
        return

    try:
        meta = probe_audio(track.audio_file.path)
    except Exception as exc:
        logger.warning('probe_audio failed for track %s: %s', track_id, exc)
        return

    update_fields = []
    if meta.get('bitrate'):
        track.bitrate = meta['bitrate']
        update_fields.append('bitrate')
    if meta.get('sample_rate'):
        track.sample_rate = meta['sample_rate']
        update_fields.append('sample_rate')

    file_size = os.path.getsize(track.audio_file.path)
    track.file_size = file_size
    update_fields.append('file_size')

    if update_fields:
        track.save(update_fields=update_fields)
