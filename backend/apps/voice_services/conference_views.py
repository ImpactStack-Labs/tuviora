"""Authenticated API for private event conference management."""

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event

from .conference import (
    can_join_conference,
    can_manage_conference,
)
from .conference_service import (
    ConferencePermissionError,
    ConferenceStateError,
    end_conference,
    start_conference,
)
from .models import EventConference
from .conference_provider import ConferenceProviderError
from .conference_access import (
    ConferenceAccessError,
    issue_access_code,
)


def conference_details(conference):
    """Return public session state without exposing the room name."""
    if conference is None:
        return {
            "status": "not_started",
            "started_at": None,
            "ended_at": None,
        }

    return {
        "status": conference.status,
        "started_at": conference.started_at,
        "ended_at": conference.ended_at,
    }


class ConferenceEventMixin:
    permission_classes = [IsAuthenticated]

    def get_event(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        if not can_join_conference(event, request.user):
            # Do not reveal private event details to outsiders.
            from django.http import Http404
            raise Http404

        return event


class EventConferenceStatusView(
    ConferenceEventMixin,
    APIView,
):
    def get(self, request, event_id):
        event = self.get_event(request, event_id)

        conference = EventConference.objects.filter(
            event=event,
        ).first()

        return Response({
            **conference_details(conference),
            "can_manage": can_manage_conference(
                event,
                request.user,
            ),
        })


class EventConferenceStartView(
    ConferenceEventMixin,
    APIView,
):
    def post(self, request, event_id):
        event = self.get_event(request, event_id)

        if not settings.VOICE_CONFERENCE_ENABLED:
            return Response(
                {"detail": "Conference calling is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            conference = start_conference(
                event,
                request.user,
            )
        except ConferencePermissionError:
            return Response(
                {"detail": "Only the organizer can start the conference."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ConferenceStateError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            conference_details(conference),
            status=status.HTTP_200_OK,
        )


class EventConferenceEndView(
    ConferenceEventMixin,
    APIView,
):
    def post(self, request, event_id):
        event = self.get_event(request, event_id)

        if not settings.VOICE_CONFERENCE_ENABLED:
            return Response(
                {"detail": "Conference calling is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            conference = end_conference(
                event,
                request.user,
                notify_provider=True,
            )
        except ConferenceProviderError:
            return Response(
                {"detail": "Unable to confirm conference termination."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ConferencePermissionError:
            return Response(
                {"detail": "Only the organizer can end the conference."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ConferenceStateError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            conference_details(conference),
            status=status.HTTP_200_OK,
        )



class EventConferenceAccessCodeView(ConferenceEventMixin, APIView):
    """Issue a short-lived PIN to an authenticated event team member."""

    def post(self, request, event_id):
        event = self.get_event(request, event_id)

        if not getattr(settings, "VOICE_CONFERENCE_ENABLED", False):
            return Response(
                {"detail": "Conference calling is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            code = issue_access_code(event, request.user)
        except ConferenceAccessError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        response = Response(
            {
                "access_code": code,
                "expires_in_seconds": 600,
            },
            status=status.HTTP_201_CREATED,
        )
        response["Cache-Control"] = "no-store"
        return response
