"""Event team authorization for private voice conferences."""

from apps.events.models import Event
from apps.events.views import task_access_for_user


def conference_role(event: Event, user):
    """Return the caller's event role, or None if unauthorized."""
    if not user or not user.is_authenticated:
        return None

    return task_access_for_user(event, user)


def can_join_conference(event: Event, user) -> bool:
    """Allow only the event organizer and accepted team members."""
    return conference_role(event, user) is not None


def can_manage_conference(event: Event, user) -> bool:
    """Only the event organizer can start or end a conference."""
    return conference_role(event, user) == "organizer"
