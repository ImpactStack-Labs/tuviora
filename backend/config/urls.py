from django.contrib import admin
from django.urls import include, path

from .views import health_check
from . import auth_views
from apps.accounts import views as account_views


urlpatterns = [
    path("api/auth/csrf/", auth_views.csrf, name="auth-csrf"),
    path("api/auth/me/", auth_views.me, name="auth-me"),
    path("api/auth/login/", auth_views.sign_in, name="auth-login"),
    path("api/auth/register/", account_views.register, name="auth-register"),
    path(
        "api/auth/verify-email/",
        account_views.verify_email,
        name="auth-verify-email",
    ),
    path("api/auth/logout/", auth_views.sign_out, name="auth-logout"),
    path("api/voice/", include("apps.voice_services.urls")),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="api-health"),
    path("api/events/", include("apps.events.urls")),
]