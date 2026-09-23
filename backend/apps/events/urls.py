from django.urls import path

from .ai_views import (
    AIIncidentAnalysisApprovalView,
    AIIncidentAnalysisDetailView,
    AIIncidentAnalysisView,
)
from .views import (
    FeedbackAnalysisView,
    FeedbackListCreateView,
    EventIncidentDetailView,
    EventIncidentListCreateView,
    EventListCreateView,
    EventTaskDetailView,
    EventTaskListCreateView,
)


urlpatterns = [
    path(
        "<int:event_id>/feedback/",
        FeedbackListCreateView.as_view(),
        name="event-feedback",
    ),
    path(
        "<int:event_id>/feedback/analysis/",
        FeedbackAnalysisView.as_view(),
        name="event-feedback-analysis",
    ),
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path(
        "<int:event_id>/tasks/",
        EventTaskListCreateView.as_view(),
        name="event-task-list-create",
    ),
    path(
        "<int:event_id>/tasks/<int:pk>/",
        EventTaskDetailView.as_view(),
        name="event-task-detail",
    ),
    path(
        "<int:event_id>/incidents/",
        EventIncidentListCreateView.as_view(),
        name="event-incident-list-create",
    ),
    path(
        "<int:event_id>/incidents/<int:pk>/",
        EventIncidentDetailView.as_view(),
        name="event-incident-detail",
    ),
    path(
        "incidents/<int:incident_id>/ai-analysis/",
        AIIncidentAnalysisView.as_view(),
        name="incident-ai-analysis",
    ),
    path(
        "incidents/<int:incident_id>/ai-analysis/detail/",
        AIIncidentAnalysisDetailView.as_view(),
        name="incident-ai-analysis-detail",
    ),
    path(
        "incidents/<int:incident_id>/ai-analysis/approve/",
        AIIncidentAnalysisApprovalView.as_view(),
        name="incident-ai-analysis-approve",
    ),
]
