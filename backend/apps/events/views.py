from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    AIFeedbackAnalysis,
    Feedback,
    Event,
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


class EventTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
            organizer=self.request.user,
        )

    def get_queryset(self):
        event = self.get_event()

        return (
            ReadinessTask.objects
            .filter(event=event)
            .select_related("event", "assignee")
        )

    def perform_create(self, serializer):
        serializer.save(event=self.get_event())


class EventTaskDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ReadinessTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ReadinessTask.objects
            .filter(event__id=self.kwargs["event_id"])
            .filter(event__organizer=self.request.user)
            .select_related("event", "assignee")
        )


class EventIncidentListCreateView(generics.ListCreateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs["event_id"],
            organizer=self.request.user,
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
        )


class EventIncidentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Incident.objects
            .filter(event__id=self.kwargs["event_id"])
            .filter(event__organizer=self.request.user)
            .select_related("event", "reported_by")
        )


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
