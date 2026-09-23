from rest_framework import serializers

from .models import AIIncidentAnalysis


class AIIncidentAnalysisSerializer(serializers.ModelSerializer):
    analysis_type = serializers.SerializerMethodField()
    incident_id = serializers.IntegerField(source="incident.id", read_only=True)

    class Meta:
        model = AIIncidentAnalysis
        fields = [
            "id",
            "incident_id",
            "analysis_type",
            "classification",
            "suggested_severity",
            "priority",
            "recommended_actions",
            "draft_message",
            "approval_status",
            "approved_by",
            "approved_at",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_analysis_type(self, obj):
        return "AI recommendation — not a verified fact"
