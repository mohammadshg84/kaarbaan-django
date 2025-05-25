from django.apps import AppConfig


class appConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        import app.signals  # این خط سیگنال‌ها را لود می‌کند