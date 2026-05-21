from django.urls import path

from .views import (
    AdminProfileView,
    AdminDashboardSummaryView,
    AdminDoctorsView,
    AdminDoctorApproveView,
    AdminDoctorDeleteView,
    AdminPatientsView,
    AdminPatientDeleteView,
    AdminSupportChatsView,
    AdminSupportChatMessagesView,
)

urlpatterns = [
    path("profile/", AdminProfileView.as_view(), name="admin-profile"),
    path("dashboard/", AdminDashboardSummaryView.as_view(), name="admin-dashboard-summary"),

    path("doctors/", AdminDoctorsView.as_view(), name="admin-doctors"),
    path("doctors/<int:doctor_id>/approve/", AdminDoctorApproveView.as_view(), name="admin-doctor-approve"),
    path("doctors/<int:doctor_id>/", AdminDoctorDeleteView.as_view(), name="admin-doctor-delete"),

    path("patients/", AdminPatientsView.as_view(), name="admin-patients"),
    path("patients/<int:patient_id>/", AdminPatientDeleteView.as_view(), name="admin-patient-delete"),

    path("support-chats/", AdminSupportChatsView.as_view(), name="admin-support-chats"),
    path("support-chats/<int:chat_id>/messages/", AdminSupportChatMessagesView.as_view(), name="admin-support-chat-messages"),
]