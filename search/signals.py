"""
Django signals to keep Elasticsearch indices in sync with the database.

django-elasticsearch-dsl handles most of the auto-sync via its
registry, but these signals cover edge cases (e.g. M2M changes).
"""

import logging
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger('search')


def _should_index() -> bool:
    """Only attempt indexing when ES is configured."""
    return bool(getattr(settings, 'ELASTICSEARCH_DSL', {}))


@receiver(m2m_changed, sender=None)
def update_index_on_m2m_change(sender, instance, action, **kwargs):
    """
    Trigger re-index when many-to-many relations change
    (e.g. artist.genres, playlist.track_list).
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not _should_index():
        return

    try:
        from django_elasticsearch_dsl.registries import registry
        registry.update(instance)
    except Exception as exc:
        logger.warning('ES index update failed for %s: %s', instance, exc)
