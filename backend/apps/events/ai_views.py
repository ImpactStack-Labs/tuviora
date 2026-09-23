from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_serializers import AIIncidentAnalysisSerializer
from .models import AIIncidentAnalysis, Incident
from .services.ai_incident_analysis import AIServiceError, analyze_incident


class AIIncidentAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident = get_object_or_404(
            Incident.objects.select_related("event"),
            pk=incident_id,
            event__organizer=request.user,
        )

        analysis_data = {
            "incident": incident,
            "classification": "",
            "suggested_severity": incident.severity,
            "priority": AIIncidentAnalysis.Priority.MEDIUM,
            "recommended_actions": [],
            "draft_message": "",
            "approval_status": AIIncidentAnalysis.ApprovalStatus.PENDING,
            "error_message": "",
        }

        try:
            result = analyze_incident(incident)

            analysis_data.update(
                {
                    "classification": result["classification"],
                    "suggested_severity": result["suggested_severity"],
                    "priority": result["priority"],
                    "recommended_actions": result["recommended_actions"],
                    "draft_message": result["draft_message"],
                }
            )

            analysis = AIIncidentAnalysis.objects.update_or_create(
                incident=incident,
                defaults=analysis_data,
            )[0]

            return Response(
                AIIncidentAnalysisSerializer(analysis).data,
                status=status.HTTP_200_OK,
            )

        except AIServiceError as exc:
            analysis_data.update(
                {
                    "approval_status": AIIncidentAnalysis.ApprovalStatus.FAILED,
                    "error_message": str(exc),
                }
            )

            analysis = AIIncidentAnalysis.objects.update_or_create(
                incident=incident,
                defaults=analysis_data,
            )[0]

            return Response(
                {
                    "detail": "AI incident analysis is currently unavailable.",
                    "analysis": AIIncidentAnalysisSerializer(analysis).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class AIIncidentAnalysisDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = get_object_or_404(
            Incident,
            pk=incident_id,
            event__organizer=request.user,
        )

        analysis = get_object_or_404(
            AIIncidentAnalysis,
            incident=incident,
        )

        return Response(
            AIIncidentAnalysisSerializer(analysis).data,
            status=status.HTTP_200_OK,
        )


class AIIncidentAnalysisApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident = get_object_or_404(
            Incident,
            pk=incident_id,
            event__organizer=request.user,
        )

        analysis = get_object_or_404(
            AIIncidentAnalysis,
            incident=incident,
        )

        if analysis.approval_status != AIIncidentAnalysis.ApprovalStatus.PENDING:
            return Response(
                {
                    "detail": (
                        "Only pending AI recommendations can be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        analysis.approval_status = AIIncidentAnalysis.ApprovalStatus.APPROVED
        analysis.approved_by = request.user
        analysis.approved_at = timezone.now()
        analysis.save(
            update_fields=[
                "approval_status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        return Response(
            AIIncidentAnalysisSerializer(analysis).data,
            status=status.HTTP_200_OK,
        )
