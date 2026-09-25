from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    AIFeedbackAnalysis,
    Feedback,
    Event,
    EventMembership,
    Incident,
    ReadinessTask,
)
from .services.ai_feedback_analysis import AIServiceError, analyze_feedback

from .serializers import (
    FeedbackSerializer,
    EventSerializer,
    IncidentSerializer,
    ReadinessTaskSerializer,
)


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Event.objects
            .filter(organizer=self.request.user)
            .select_related("organizer")
        )

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)



class EventPublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        event = get_object_or_404(
            Event,
            pk=event_id,
            organizer=request.user,
        )

        if event.status != Event.Status.DRAFT:
            return Response(
                {"detail": "Only draft events can be published."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event.status = Event.Status.PUBLISHED
        event.save(update_fields=["status", "updated_at"])

        return Response(EventSerializer(event).data)


# TEAM_TASK_ACCESS_V1
def task_access_for_user(event, user):
    """Resolve permissions separately for each event."""
    if event.organizer_id == user.pk:
        return "organizer"

    membership = EventMembership.objects.filter(
        event=event,
        user=user,
    ).first()

    if membership is None:
        return None

    return membership.role


def accessible_task_event(event_id, user):
    """Return an event only if this user belongs to its team."""
    from django.http import Http404

    event = get_object_or_404(Event, id=event_id)

    if task_access_for_user(event, user) is None:
        raise Http404

    return event


class EventTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return accessible_task_event(
            self.kwargs["event_id"],
            self.request.user,
        )

    def get_queryset(self):
        event = self.get_event()
        role = task_access_for_user(event, self.request.user)

        if role is None:
            # Do not reveal tasks belonging to unrelated events.
            return ReadinessTask.objects.none()

        tasks = ReadinessTask.objects.filter(
            event=event,
        ).select_related("event", "assignee")

        if role == EventMembership.Role.MEMBER:
            return tasks.filter(assignee=self.request.user)

        return tasks

    def perform_create(self, serializer):
        event = self.get_event()

        if event.organizer_id != self.request.user.pk:
            raise PermissionDenied(
                "Only the event organizer can create tasks."
            )

        serializer.save(event=event)


class EventTaskDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        event = accessible_task_event(
            self.kwargs["event_id"],
            self.request.user,
        )

        role = task_access_for_user(event, self.request.user)

        if role is None:
            return ReadinessTask.objects.none()

        tasks = ReadinessTask.objects.filter(
            event=event,
        ).select_related("event", "assignee")

        if role == EventMembership.Role.MEMBER:
            return tasks.filter(assignee=self.request.user)

        return tasks

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()

        if task.event.organizer_id != request.user.pk:
            # Managers and members can update progress, but cannot
            # change the task title, deadline, or assignee.
            if set(request.data) != {"status"}:
                raise PermissionDenied(
                    "You can update task status only."
                )

        return super().partial_update(request, *args, **kwargs)


class EventIncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return accessible_task_event(
            self.kwargs["event_id"],
            self.request.user,
        )

    def get_queryset(self):
        event = self.get_event()

        return (
            Incident.objects
            .filter(event=event)
            .select_related("event", "reported_by")
        )

    def perform_create(self, serializer):
        serializer.save(
            event=self.get_event(),
            reported_by=self.request.user,
            status=Incident.Status.OPEN,
        )


class EventIncidentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        event = accessible_task_event(
            self.kwargs["event_id"],
            self.request.user,
        )

        return (
            Incident.objects
            .filter(event=event)
            .select_related("event", "reported_by")
        )

    def partial_update(self, request, *args, **kwargs):
        incident = self.get_object()
        role = task_access_for_user(
            incident.event,
            request.user,
        )

        if role not in {
            "organizer",
            EventMembership.Role.MANAGER,
        }:
            raise PermissionDenied(
                "Only the organizer or event manager "
                "can update incidents."
            )

        return super().partial_update(request, *args, **kwargs)


class FeedbackListCreateView(generics.ListCreateAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(
            event_id=self.kwargs["event_id"]
        ).select_related("attendee", "event")

    def perform_create(self, serializer):
        event = get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
        )

        serializer.save(
            event=event,
            attendee=self.request.user,
        )


class FeedbackAnalysisView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
            organizer=self.request.user,
        )

    def get(self, request, *args, **kwargs):
        event = self.get_event()

        analysis = getattr(
            event,
            "ai_feedback_analysis",
            None,
        )

        if analysis is None:
            return Response(
                {
                    "analysis_type": "AI-generated analysis",
                    "message": "No feedback analysis has been generated yet.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "id": analysis.id,
                "event": event.id,
                "themes": analysis.themes,
                "concerns_summary": analysis.concerns_summary,
                "suggested_improvements": analysis.suggested_improvements,
                "analysis_type": analysis.analysis_type,
                "error_message": analysis.error_message,
                "created_at": analysis.created_at,
                "updated_at": analysis.updated_at,
            }
        )

    def post(self, request, *args, **kwargs):
        event = self.get_event()

        feedback_items = list(
            Feedback.objects.filter(event=event)
        )

        if not feedback_items:
            analysis, _ = AIFeedbackAnalysis.objects.update_or_create(
                event=event,
                defaults={
                    "themes": [],
                    "concerns_summary": "",
                    "suggested_improvements": [],
                    "analysis_type": "AI-generated analysis",
                    "error_message": "",
                },
            )

            return Response(
                {
                    "id": analysis.id,
                    "event": event.id,
                    "themes": [],
                    "concerns_summary": "",
                    "suggested_improvements": [],
                    "analysis_type": "AI-generated analysis",
                    "message": "No attendee feedback is available for analysis.",
                },
                status=status.HTTP_200_OK,
            )

        try:
            result = analyze_feedback(feedback_items)
        except AIServiceError as exc:
            analysis, _ = AIFeedbackAnalysis.objects.update_or_create(
                event=event,
                defaults={
                    "themes": [],
                    "concerns_summary": "",
                    "suggested_improvements": [],
                    "analysis_type": "AI-generated analysis",
                    "error_message": str(exc),
                },
            )

            return Response(
                {
                    "id": analysis.id,
                    "event": event.id,
                    "analysis_type": "AI-generated analysis",
                    "error_message": analysis.error_message,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        analysis, _ = AIFeedbackAnalysis.objects.update_or_create(
            event=event,
            defaults={
                "themes": result["themes"],
                "concerns_summary": result["concerns_summary"],
                "suggested_improvements": result["suggested_improvements"],
                "analysis_type": "AI-generated analysis",
                "error_message": "",
            },
        )

        return Response(
            {
                "id": analysis.id,
                "event": event.id,
                "themes": analysis.themes,
                "concerns_summary": analysis.concerns_summary,
                "suggested_improvements": analysis.suggested_improvements,
                "analysis_type": analysis.analysis_type,
                "created_at": analysis.created_at,
                "updated_at": analysis.updated_at,
            },
            status=status.HTTP_200_OK,
        )
