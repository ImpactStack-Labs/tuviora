from django.contrib import admin
from django.urls import include, path

from .views import health_check


urlpatterns = [
    path("api/voice/", include("apps.voice_services.urls")),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="api-health"),
    path("api/events/", include("apps.events.urls")),
]