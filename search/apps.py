from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search'
    verbose_name = 'Elasticsearch Search'

    def ready(self):
        import search.signals  # noqa: F401
