"""API for triggering critical-incident voice call escalation."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import EventMembership, Incident
from apps.events.views import task_access_for_user

from .incident_calls import IncidentCallStateError, call_team_for_incident


class IncidentCallTeamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, incident_id):
        incident = get_object_or_404(
            Incident,
            pk=incident_id,
            event_id=event_id,
        )
        role = task_access_for_user(incident.event, request.user)

        if role is None:
            # Do not reveal private event/incident details to outsiders.
            raise Http404

        if role not in ("organizer", EventMembership.Role.MANAGER):
            return Response(
                {
                    "detail": (
                        "Only the organizer or event managers "
                        "can call the team."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not settings.VOICE_CRITICAL_CALLS_ENABLED:
            return Response(
                {"detail": "Critical incident calling is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = call_team_for_incident(incident)
        except IncidentCallStateError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)
