from django.urls import path

from .views import (
    EventIncidentDetailView,
    EventIncidentListCreateView,
    EventListCreateView,
    EventTaskDetailView,
    EventTaskListCreateView,
)


urlpatterns = [
    path(
        "",
        EventListCreateView.as_view(),
        name="event-list-create",
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
]
