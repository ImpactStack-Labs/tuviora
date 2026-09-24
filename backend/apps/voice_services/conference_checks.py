"""Deployment checks for private event conferences."""

from django.conf import settings
from django.core.checks import Error, register


@register()
def check_conference_configuration(app_configs, **kwargs):
    """Prevent enabling conferences without a shared cache."""
    if not getattr(settings, "VOICE_CONFERENCE_ENABLED", False):
        return []

    errors = []

    cache_config = settings.CACHES.get("default", {})
    cache_backend = cache_config.get("BACKEND", "")

    if cache_backend not in {
        "django.core.cache.backends.redis.RedisCache",
        "django_redis.cache.RedisCache",
    }:
        errors.append(
            Error(
                "Private voice conferences require a shared Redis cache.",
                hint=(
                    "Configure a shared Redis cache before setting "
                    "VOICE_CONFERENCE_ENABLED=true."
                ),
                id="voice_conference.E001",
            )
        )

    if not getattr(settings, "AT_VOICE_NUMBER", ""):
        errors.append(
            Error(
                "The Africa's Talking Voice number is not configured.",
                hint="Set AT_VOICE_NUMBER in the backend environment.",
                id="voice_conference.E002",
            )
        )

    return errors
