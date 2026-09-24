from .public_views import PublicEventDetailView, PublicEventListView
from .registration_views import (
    CancelEventRegistrationView,
    EventRegistrationView,
    MyEventRegistrationView,
    MyRegistrationsListView,
)

from .team_views import (
    EventTeamView,
    EventInvitationView,
    EventInvitationRevokeView,
    InvitationAcceptView,
)

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
    EventPublishView,
    EventTaskDetailView,
    EventTaskListCreateView,
)


urlpatterns = [
    path(
        "registrations/me/",
        MyRegistrationsListView.as_view(),
        name="my-registrations-list",
    ),
    path(
        "public/",
        PublicEventListView.as_view(),
        name="public-event-list",
    ),
    path(
        "public/<int:pk>/",
        PublicEventDetailView.as_view(),
        name="public-event-detail",
    ),
    path(
        "<int:event_id>/registrations/",
        EventRegistrationView.as_view(),
        name="event-registrations",
    ),
    path(
        "<int:event_id>/registrations/me/",
        MyEventRegistrationView.as_view(),
        name="my-event-registration",
    ),
    path(
        "<int:event_id>/registrations/me/cancel/",
        CancelEventRegistrationView.as_view(),
        name="cancel-event-registration",
    ),

    path(
        "invitations/accept/",
        InvitationAcceptView.as_view(),
        name="event-invitation-accept",
    ),
    path(
        "<int:event_id>/team/",
        EventTeamView.as_view(),
        name="event-team",
    ),
    path(
        "<int:event_id>/invitations/",
        EventInvitationView.as_view(),
        name="event-invitations",
    ),
    path(
        "<int:event_id>/invitations/<int:invitation_id>/revoke/",
        EventInvitationRevokeView.as_view(),
        name="event-invitation-revoke",
    ),
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
        "<int:event_id>/publish/",
        EventPublishView.as_view(),
        name="event-publish",
    ),
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
