from django.urls import path

from .views import (
    DoctorProfileView,
    DoctorAppointmentsView,
    DoctorAppointmentStatusView,
    DoctorChatsView,
    DoctorChatMessagesView,
    DoctorSupportChatsView,
    DoctorSupportChatMessagesView,
    DoctorDashboardSummaryView,
    DoctorAiScansView,
    DoctorAiScanDetailView,
    DoctorAiScanAnalysisView,
)

urlpatterns = [
    path("profile/", DoctorProfileView.as_view(), name="doctor-profile"),

    path("appointments/", DoctorAppointmentsView.as_view(), name="doctor-appointments"),
    path("appointments/<int:appointment_id>/status/", DoctorAppointmentStatusView.as_view(), name="doctor-appointment-status"),

    path("chats/", DoctorChatsView.as_view(), name="doctor-chats"),
    path("chats/<int:chat_id>/messages/", DoctorChatMessagesView.as_view(), name="doctor-chat-messages"),

    path("support-chats/", DoctorSupportChatsView.as_view(), name="doctor-support-chats"),
    path("support-chats/<int:chat_id>/messages/", DoctorSupportChatMessagesView.as_view(), name="doctor-support-chat-messages"),

    path("dashboard/", DoctorDashboardSummaryView.as_view(), name="doctor-dashboard-summary"),

    path("ai-scans/", DoctorAiScansView.as_view(), name="doctor-ai-scans"),
    path("ai-scans/<int:scan_id>/", DoctorAiScanDetailView.as_view(), name="doctor-ai-scan-detail"),
    path("ai-scans/<int:scan_id>/analysis/", DoctorAiScanAnalysisView.as_view(), name="doctor-ai-scan-analysis"),
]