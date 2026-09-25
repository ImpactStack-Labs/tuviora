from django.urls import path

from .conference_views import (
    EventConferenceAccessCodeView,
    EventConferenceEndView,
    EventConferenceStartView,
    EventConferenceStatusView,
)
from .conference_callback import conference_callback
from .incident_call_views import IncidentCallTeamView
from .views import voice_callback


urlpatterns = [
    path(
        "conference/callback/",
        conference_callback,
        name="conference-callback",
    ),
    path(
        "callback/",
        voice_callback,
        name="voice-callback",
    ),
    path(
        "events/<int:event_id>/conference/",
        EventConferenceStatusView.as_view(),
        name="event-conference-status",
    ),
    path(
        "events/<int:event_id>/conference/start/",
        EventConferenceStartView.as_view(),
        name="event-conference-start",
    ),
    path(
        "events/<int:event_id>/conference/access-code/",
        EventConferenceAccessCodeView.as_view(),
        name="event-conference-access-code",
    ),
    path(
        "events/<int:event_id>/conference/end/",
        EventConferenceEndView.as_view(),
        name="event-conference-end",
    ),
    path(
        "events/<int:event_id>/incidents/<int:incident_id>/call-team/",
        IncidentCallTeamView.as_view(),
        name="event-incident-call-team",
    ),
]
