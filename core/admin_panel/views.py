from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsAdmin

from .serializers import (
    AdminProfileUpdateSerializer,
    AdminMessageCreateSerializer,
)

from .services import (
    get_admin_profile,
    update_admin_profile,
    get_admin_dashboard_summary,
    get_admin_doctors,
    approve_admin_doctor,
    delete_admin_doctor,
    get_admin_patients,
    delete_admin_patient,
    get_admin_support_chats,
    get_admin_support_chat_messages,
    send_admin_support_message,
)
class AdminProfileView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        profile = get_admin_profile(request.user)
        return Response(profile)

    def put(self, request):
        serializer = AdminProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = update_admin_profile(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Admin profile updated successfully",
            "profile": profile
        })
    
class AdminDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        summary = get_admin_dashboard_summary(request.user)

        return Response(summary)
    

class AdminDoctorsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        doctors = get_admin_doctors(request.user)
        return Response(doctors)


class AdminDoctorApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, doctor_id):
        doctor = approve_admin_doctor(request.user, doctor_id)

        return Response({
            "message": "Doctor approved successfully",
            "doctor": doctor
        })


class AdminDoctorDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, doctor_id):
        result = delete_admin_doctor(request.user, doctor_id)
        return Response(result)
    

class AdminPatientsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        patients = get_admin_patients(request.user)
        return Response(patients)


class AdminPatientDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, patient_id):
        result = delete_admin_patient(request.user, patient_id)
        return Response(result)
    

class AdminSupportChatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        chats = get_admin_support_chats(request.user)
        return Response(chats)


class AdminSupportChatMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, chat_id):
        messages = get_admin_support_chat_messages(
            request.user,
            chat_id
        )

        return Response(messages)

    def post(self, request, chat_id):
        serializer = AdminMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = send_admin_support_message(
            request.user,
            chat_id,
            serializer.validated_data
        )

        return Response({
            "message": "Support message sent successfully",
            "data": message
        }, status=201)