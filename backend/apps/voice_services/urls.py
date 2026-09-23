from django.urls import path

from .views import voice_callback


urlpatterns = [
    path(
        "callback/",
        voice_callback,
        name="voice-callback",
    ),
]
