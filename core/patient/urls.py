from django.urls import path
from .views import (
    PatientProfileView,
    PatientDoctorsListView,
    PatientAppointmentsView,
    PatientDashboardSummaryView,
    PatientChatsView,
    PatientChatMessagesView,
    PatientSupportChatsView,
    PatientSupportChatMessagesView,
    PatientRatingsView,
    PatientAiScansView,
    PatientAiScanDetailView,
)


urlpatterns = [
    path("profile/", PatientProfileView.as_view(), name="patient-profile"),
    path("doctors/", PatientDoctorsListView.as_view(), name="patient-doctors"),
    path("appointments/", PatientAppointmentsView.as_view(), name="patient-appointments"),
    path("dashboard/", PatientDashboardSummaryView.as_view(), name="patient-dashboard-summary"),

    path("chats/", PatientChatsView.as_view(), name="patient-chats"),
    path("chats/<int:chat_id>/messages/", PatientChatMessagesView.as_view(), name="patient-chat-messages"),

    path("support-chats/", PatientSupportChatsView.as_view(), name="patient-support-chats"),
    path("support-chats/<int:chat_id>/messages/", PatientSupportChatMessagesView.as_view(), name="patient-support-chat-messages"),

    path("ratings/", PatientRatingsView.as_view(), name="patient-ratings"),

    path("ai-scans/", PatientAiScansView.as_view(), name="patient-ai-scans"),
    path("ai-scans/<int:scan_id>/", PatientAiScanDetailView.as_view(), name="patient-ai-scan-detail"),
]