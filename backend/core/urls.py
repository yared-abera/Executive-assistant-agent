"""
URL configuration for core project.
"""

from django.contrib import admin
from django.urls import path

from assistant.views import (
    AddPreferenceView,
    AgentCommandStreamView,
    AgentCommandView,
    CalendarEventsView,
    DailyBriefingJobView,
    GoogleCalendarWebhookView,
    PendingActionApproveView,
    PendingActionListView,
    PendingActionRejectView,
    PreferenceDeleteView,
    PreferenceListView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/agent/command/", AgentCommandView.as_view(), name="agent-command"),
    path(
        "api/agent/command/stream/",
        AgentCommandStreamView.as_view(),
        name="agent-command-stream",
    ),
    path("api/agent/preference/", AddPreferenceView.as_view(), name="add-preference"),
    path(
        "api/agent/preferences/",
        PreferenceListView.as_view(),
        name="list-preferences",
    ),
    path(
        "api/agent/preference/<int:pk>/",
        PreferenceDeleteView.as_view(),
        name="delete-preference",
    ),
    path("api/calendar/events/", CalendarEventsView.as_view(), name="calendar-events"),
    path("api/agent/pending/", PendingActionListView.as_view(), name="pending-list"),
    path(
        "api/agent/pending/<int:pk>/approve/",
        PendingActionApproveView.as_view(),
        name="pending-approve",
    ),
    path(
        "api/agent/pending/<int:pk>/reject/",
        PendingActionRejectView.as_view(),
        name="pending-reject",
    ),
    path(
        "api/webhooks/google-calendar/",
        GoogleCalendarWebhookView.as_view(),
        name="calendar-webhook",
    ),
    path(
        "api/jobs/daily-briefing/",
        DailyBriefingJobView.as_view(),
        name="daily-briefing",
    ),
]
