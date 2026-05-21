from django.urls import path, include


from .views import (
    PatientRegisterView,
    VerifyOTPView,
    DoctorRegisterView,
    DoctorOTPVerifyView,
    PatientDashboardView,
    DoctorDashboardView,
)

urlpatterns = [
    path("register/patient/", PatientRegisterView.as_view(), name="register-patient"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),

    path("register/doctor/", DoctorRegisterView.as_view(), name="register-doctor"),
    path("verify-doctor-otp/", DoctorOTPVerifyView.as_view(), name="verify-doctor-otp"),

    path("dashboard/patient/", PatientDashboardView.as_view(), name="patient-dashboard"),
    path("dashboard/doctor/", DoctorDashboardView.as_view(), name="doctor-dashboard"),
    
    path("patient/", include("core.patient.urls")),
    path("doctor/", include("core.doctor.urls")),
    path("admin/", include("core.admin_panel.urls")),
]