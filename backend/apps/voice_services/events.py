"""Public event information for Tuviora's Voice assistant."""

from datetime import datetime

from apps.events.models import Event


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
