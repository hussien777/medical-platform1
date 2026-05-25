from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from core.serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from core.services import request_password_reset, confirm_password_reset
from core.permissions import IsPatient, IsDoctor

from .serializers import (
    PatientRegisterSerializer,
    VerifyOTPSerializer,
    DoctorRegisterSerializer,
)

from .services import (
    register_patient,
    verify_patient_otp,
    register_doctor,
    verify_doctor_otp,
)


# =========================
# PATIENT REGISTER
# =========================
class PatientRegisterView(APIView):
    def post(self, request):
        serializer = PatientRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = register_patient(serializer.validated_data)

        return Response(
            {
                "message": "Patient registered successfully. Check OTP.",
                "user_id": user.user_id,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================
# PATIENT OTP VERIFY
# =========================
class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = verify_patient_otp(serializer.validated_data)

        return Response(
            {
                "message": "Patient account verified successfully.",
                "user_id": user.user_id,
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


# =========================
# DOCTOR REGISTER
# =========================
class DoctorRegisterView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DoctorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = register_doctor(serializer.validated_data)

        return Response(
            {
                "message": "Doctor registered successfully. Check OTP.",
                "user_id": user.user_id,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================
# DOCTOR OTP VERIFY
# =========================
class DoctorOTPVerifyView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = verify_doctor_otp(serializer.validated_data)

        return Response(
            {
                "message": "Doctor account verified successfully.",
                "user_id": user.user_id,
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


# =========================
# PATIENT DASHBOARD TEST
# =========================
class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        return Response({"message": "Welcome patient"})


# =========================
# DOCTOR DASHBOARD TEST
# =========================
class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        return Response({"message": "Welcome doctor"})
    


# =========================
# PASSWORD RESET REQUEST VIEW
# =========================
class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            result = request_password_reset(serializer.validated_data)
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# PASSWORD RESET CONFIRM VIEW
# =========================
class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            result = confirm_password_reset(serializer.validated_data)
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)