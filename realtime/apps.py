from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'realtime'
    verbose_name = 'Real-time Notifications'

    def ready(self):
        import realtime.signals  # noqa: F401
