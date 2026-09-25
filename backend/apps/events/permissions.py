"""Shared per-event permission checks."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Event, EventMembership
from .views import task_access_for_user

LEAD_ROLES = ("organizer", EventMembership.Role.MANAGER)


def lead_event_or_deny(event_id, user):
    """Return the event when user is its organizer or a manager.

    Outsiders get 404 so private events stay hidden; members get 403.
    """
    event = get_object_or_404(Event, pk=event_id)
    role = task_access_for_user(event, user)

    if role is None:
        raise Http404

    if role not in LEAD_ROLES:
        raise PermissionDenied(
            "Only the organizer or event managers can do this."
        )

    return event
