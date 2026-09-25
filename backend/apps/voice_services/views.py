"""Africa's Talking Voice callbacks for Tuviora."""

from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .events import describe_event, get_public_event
from .languages import LANGUAGES, LANGUAGE_SELECTION
from .menus import get_message
from .models import PendingVoiceCall


SESSION_TIMEOUT = 3600


def voice_response(message, callback_url=None, finish=False):
    """Generate an Africa's Talking Voice XML response."""
    root = Element("Response")

    if callback_url and not finish:
        gather = SubElement(
            root,
            "GetDigits",
            {
                "timeout": "15",
                "finishOnKey": "#",
                "callbackUrl": callback_url,
            },
        )
        SubElement(gather, "Say").text = message
    else:
        SubElement(root, "Say").text = message

    if finish:
        SubElement(root, "Hangup")

    xml = tostring(root, encoding="utf-8", xml_declaration=True)

    return HttpResponse(xml, content_type="application/xml")


def session_key(session_id):
    return f"tuviora_voice:{session_id}"


def callback_url(request):
    return request.build_absolute_uri(request.path)


def _handle_outbound_callback(request):
    """Speak the message queued for this outbound call, then hang up.

    Africa's Talking's outbound-call callback payload is expected to
    include `destinationNumber` — verify this field name against a real
    sandbox call if it ever stops matching.
    """
    phone_number = request.POST.get("destinationNumber", "").strip()

    pending = (
        PendingVoiceCall.objects
        .filter(
            phone_number=phone_number,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )

    if pending is None:
        return voice_response("Goodbye.", finish=True)

    message = pending.message
    pending.delete()

    return voice_response(message, finish=True)


@csrf_exempt
@require_POST
def voice_callback(request):
    """Handle incoming calls and subsequent keypad selections."""
    if request.POST.get("direction", "") == "Outbound":
        return _handle_outbound_callback(request)

    session_id = request.POST.get("sessionId", "").strip()
    digits = request.POST.get("dtmfDigits", "").strip()

    if not session_id:
        return HttpResponse(
            "Missing sessionId",
            status=400,
        )

    key = session_key(session_id)
    session = cache.get(key)

    # New caller: begin with language selection.
    if session is None:
        cache.set(
            key,
            {"stage": "language", "language": None},
            SESSION_TIMEOUT,
        )

        return voice_response(
            LANGUAGE_SELECTION,
            callback_url(request),
        )

    stage = session["stage"]
    language = session["language"]

    if stage == "language":
        if digits not in LANGUAGES:
            return voice_response(
                "Invalid language selection. "
                + LANGUAGE_SELECTION,
                callback_url(request),
            )

        language = LANGUAGES[digits]["code"]

        cache.set(
            key,
            {"stage": "main", "language": language},
            SESSION_TIMEOUT,
        )

        return voice_response(
            get_message(language, "main"),
            callback_url(request),
        )

    if stage == "main":
        if digits == "0":
            cache.delete(key)

            return voice_response(
                get_message(language, "goodbye"),
                finish=True,
            )

        if digits == "9":
            cache.set(
                key,
                {"stage": "language", "language": None},
                SESSION_TIMEOUT,
            )

            return voice_response(
                LANGUAGE_SELECTION,
                callback_url(request),
            )

        options = {
            "1": "event_information",
            "2": "venue_directions",
            "3": "registration_assistance",
        }

        if digits == "1":
            cache.set(
                key,
                {"stage": "event_id", "language": language},
                SESSION_TIMEOUT,
            )

            prompts = {
                "eng": "Enter your event ID, followed by hash. Press star to return to the main menu.",
                "swa": "Tafadhali ingiza nambari ya tukio lako, kisha alama ya reli. Bonyeza nyota kurudi kwenye menyu kuu.",
                "lug": "Yingiza ennamba y'omukolo gwo, oluvannyuma onyige akabonero ka hash. Nyiga emmunyeenye okuddayo ku menu enkulu.",
            }

            return voice_response(
                prompts.get(language, prompts["eng"]),
                callback_url(request),
            )

        if digits in options:
            cache.set(
                key,
                {"stage": "detail", "language": language},
                SESSION_TIMEOUT,
            )

            return voice_response(
                get_message(language, options[digits]),
                callback_url(request),
            )

        return voice_response(
            get_message(language, "invalid")
            + " "
            + get_message(language, "main"),
            callback_url(request),
        )

    if stage == "event_id":
        if digits == "*":
            cache.set(
                key,
                {"stage": "main", "language": language},
                SESSION_TIMEOUT,
            )
            return voice_response(
                get_message(language, "main"),
                callback_url(request),
            )

        if digits == "0":
            cache.delete(key)
            return voice_response(
                get_message(language, "goodbye"),
                finish=True,
            )

        event = get_public_event(digits)

        if event is None:
            messages = {
                "eng": "We could not find that published event. Please try again.",
                "swa": "Hatukupata tukio hilo lililochapishwa. Tafadhali jaribu tena.",
                "lug": "Tetulabye mukolo ogwo ogulangiriddwa. Gezaako nate.",
            }
            return voice_response(
                messages.get(language, messages["eng"]),
                callback_url(request),
            )

        cache.set(
            key,
            {"stage": "detail", "language": language},
            SESSION_TIMEOUT,
        )

        return voice_response(
            describe_event(event, language)
            + " "
            + {
                "eng": "Press 9 to return to the main menu.",
                "swa": "Bonyeza 9 kurudi kwenye menyu kuu.",
                "lug": "Nyiga 9 okuddayo ku menu enkulu.",
            }.get(language, "Press 9 to return to the main menu."),
            callback_url(request),
        )

    if stage == "detail":
        if digits == "9":
            cache.set(
                key,
                {"stage": "main", "language": language},
                SESSION_TIMEOUT,
            )

            return voice_response(
                get_message(language, "main"),
                callback_url(request),
            )

        if digits == "0":
            cache.delete(key)

            return voice_response(
                get_message(language, "goodbye"),
                finish=True,
            )

        return voice_response(
            get_message(language, "invalid")
            + " "
            + get_message(language, "main"),
            callback_url(request),
        )

    cache.delete(key)

    return voice_response(
        LANGUAGE_SELECTION,
        callback_url(request),
    )
