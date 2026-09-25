"""Public event information for Tuviora's Voice assistant."""

from datetime import datetime

from apps.sms.models import SMSPreference
from apps.events.models import Event, EventRegistration


def get_public_event(event_id):
    """Return a published event, or None if it is not publicly available."""
    if not str(event_id).isdigit():
        return None

    return (
        Event.objects
        .filter(
            pk=int(event_id),
            status=Event.Status.PUBLISHED,
        )
        .first()
    )


def get_registration(event_id, phone_number):
    """Return the caller's own registration for an event, or None.

    ``phone_number`` must already be a verified caller identity (e.g. the
    telco-assigned number from a USSD session), not user-supplied input.
    """
    if not str(event_id).isdigit():
        return None

    # A phone saved on several accounts is ambiguous: treat it as unknown.
    matches = list(
        SMSPreference.objects.filter(phone_number=phone_number)[:2]
    )
    if len(matches) != 1:
        return None
    preference = matches[0]

    return (
        EventRegistration.objects
        .select_related("event", "ticket_type")
        .filter(event_id=int(event_id), user_id=preference.user_id)
        .first()
    )


def describe_event(event, language="eng"):
    """Prepare event information for the caller's selected language."""
    date_text = event.date.strftime("%d %B %Y")
    start = event.start_time.strftime("%H:%M")
    end = event.end_time.strftime("%H:%M")

    # The event's own name and venue are retained as entered by its organizer.
    # These are interface translations, not translations of event content.
    templates = {
        "eng": (
            "{name} takes place on {date}, "
            "from {start} to {end}."
        ),
        "swa": (
            "Tukio la {name} litafanyika tarehe {date}, "
            "kuanzia saa {start} hadi {end}."
        ),
        "lug": (
            "Omukolo gwa {name} gujja kubeerawo nga {date}, "
            "okuva ku ssaawa {start} okutuuka ku {end}."
        ),
    }

    template = templates.get(language, templates["eng"])

    return template.format(
        name=event.name,
        date=date_text,
        start=start,
        end=end,
    )
