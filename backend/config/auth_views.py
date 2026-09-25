import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def user_payload(user):
    from apps.events.models import Event, EventMembership

    organized_events = list(
        Event.objects.filter(organizer=user)
        .values("id", "name")
    )

    memberships = list(
        EventMembership.objects.filter(user=user)
        .select_related("event")
        .values(
            "event_id",
            "event__name",
            "role",
        )
    )

    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "is_staff": user.is_staff,
        "is_organizer": bool(organized_events),
        "organized_events": organized_events,
        "team_memberships": [
            {
                "event_id": membership["event_id"],
                "event_name": membership["event__name"],
                "role": membership["role"],
            }
            for membership in memberships
        ],
    }


@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie initialized."})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Authentication required."},
            status=401,
        )

    return JsonResponse({"user": user_payload(request.user)})


@require_POST
def sign_in(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"detail": "Invalid JSON request."},
            status=400,
        )

    username = data.get("username", "")
    password = data.get("password", "")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None or not user.is_active:
        # Right password on an unverified account: say why, since
        # "invalid password" sends people in circles. Wrong passwords
        # still get the generic message, so nothing new is revealed.
        pending = get_user_model().objects.filter(
            username=username, is_active=False,
        ).first()
        if pending is not None and pending.check_password(password):
            return JsonResponse(
                {"detail": "Please verify your email before signing in. "
                           "Check your inbox for the verification link."},
                status=400,
            )

        return JsonResponse(
            {"detail": "Invalid username or password."},
            status=400,
        )

    login(request, user)

    return JsonResponse({"user": user_payload(user)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"detail": "Signed out successfully."})
