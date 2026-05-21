from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from core.permissions import IsDoctor

from .serializers import (
    DoctorProfileUpdateSerializer,
    DoctorAppointmentStatusUpdateSerializer,
    DoctorMessageCreateSerializer,
    DoctorAiScanAnalysisUpdateSerializer,
)
from .services import (
    get_doctor_profile,
    update_doctor_profile,
    get_doctor_appointments,
    update_doctor_appointment_status,
    delete_doctor_appointment,
    get_doctor_chats,
    get_doctor_chat_messages,
    send_doctor_chat_message,
    create_or_get_doctor_support_chat,
    get_doctor_support_chats,
    get_doctor_support_chat_messages,
    send_doctor_support_message,
    get_doctor_dashboard_summary,
    get_doctor_ai_scans,
    get_doctor_ai_scan_detail,
    update_doctor_ai_scan_analysis,
)
class DoctorProfileView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile = get_doctor_profile(request.user)
        return Response(profile)

    def put(self, request):
        serializer = DoctorProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = update_doctor_profile(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Doctor profile updated successfully",
            "profile": profile
        })
    

class DoctorAppointmentsView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        appointments = get_doctor_appointments(request.user)

        return Response({
            "appointments": appointments
        })


class DoctorAppointmentStatusView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def patch(self, request, appointment_id):
        serializer = DoctorAppointmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = update_doctor_appointment_status(
            request.user,
            appointment_id,
            serializer.validated_data
        )

        return Response({
            "message": "Appointment status updated successfully",
            "appointment": appointment
        })

    def delete(self, request, appointment_id):
        result = delete_doctor_appointment(
            request.user,
            appointment_id
        )

        return Response(result)
    
class DoctorChatsView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        chats = get_doctor_chats(request.user)

        return Response({
            "chats": chats
        })


class DoctorChatMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, chat_id):
        messages = get_doctor_chat_messages(request.user, chat_id)

        return Response({
            "messages": messages
        })

    def post(self, request, chat_id):
        serializer = DoctorMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = send_doctor_chat_message(
            request.user,
            chat_id,
            serializer.validated_data
        )

        return Response({
            "message": "Message sent successfully",
            "data": message
        }, status=201)
    

class DoctorSupportChatsView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        chats = get_doctor_support_chats(request.user)

        return Response({
            "support_chats": chats
        })

    def post(self, request):
        chat = create_or_get_doctor_support_chat(request.user)

        return Response({
            "message": "Support chat opened successfully",
            "chat": chat
        }, status=201)


class DoctorSupportChatMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, chat_id):
        messages = get_doctor_support_chat_messages(request.user, chat_id)

        return Response({
            "messages": messages
        })

    def post(self, request, chat_id):
        serializer = DoctorMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = send_doctor_support_message(
            request.user,
            chat_id,
            serializer.validated_data
        )

        return Response({
            "message": "Support message sent successfully",
            "data": message
        }, status=201)
    

class DoctorDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        summary = get_doctor_dashboard_summary(request.user)

        return Response(summary)
    


class DoctorAiScansView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        scans = get_doctor_ai_scans(request.user)

        return Response({
            "scans": scans
        })


class DoctorAiScanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request, scan_id):
        scan = get_doctor_ai_scan_detail(
            request.user,
            scan_id
        )

        return Response(scan)


class DoctorAiScanAnalysisView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def patch(self, request, scan_id):
        serializer = DoctorAiScanAnalysisUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scan = update_doctor_ai_scan_analysis(
            request.user,
            scan_id,
            serializer.validated_data
        )

        return Response({
            "message": "AI scan analysis updated successfully",
            "scan": scan
        })