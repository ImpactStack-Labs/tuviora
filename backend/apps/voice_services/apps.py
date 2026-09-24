from django.apps import AppConfig


class VoiceServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.voice_services"
    verbose_name = "Tuviora Voice Services"

    def ready(self):
        """Register private conference deployment checks."""
        from . import conference_checks  # noqa: F401
