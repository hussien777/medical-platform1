from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsPatient

from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import (
    PatientProfileUpdateSerializer,
    PatientAppointmentCreateSerializer,
    PatientChatCreateSerializer,
    PatientMessageCreateSerializer,
    PatientRatingCreateSerializer,
    PatientAiScanUploadSerializer,
)

from .services import (
    get_patient_profile,
    update_patient_profile,
    get_available_doctors,
    create_patient_appointment,
    get_patient_appointments,
    get_patient_dashboard_summary,
    create_or_get_patient_doctor_chat,
    get_patient_chats,
    get_chat_messages,
    send_patient_chat_message,

    create_or_get_patient_support_chat,
    get_patient_support_chats,
    get_support_chat_messages,
    send_patient_support_message,
    create_patient_rating,
    get_patient_ratings,
    create_patient_ai_scan,
    get_patient_ai_scans,
    get_patient_ai_scan_detail,
)

class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        profile = get_patient_profile(request.user)
        return Response(profile)

    def put(self, request):
        serializer = PatientProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = update_patient_profile(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Patient profile updated successfully",
            "profile": profile
        })
    

class PatientDoctorsListView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        doctors = get_available_doctors()
        return Response({
            "doctors": doctors
        })
    
class PatientAppointmentsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        appointments = get_patient_appointments(request.user)

        return Response({
            "appointments": appointments
        })

    def post(self, request):
        serializer = PatientAppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = create_patient_appointment(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Appointment booked successfully",
            "appointment": appointment
        }, status=201)
    

class PatientDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        summary = get_patient_dashboard_summary(request.user)

        return Response(summary)
    
class PatientChatsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        chats = get_patient_chats(request.user)

        return Response({
            "chats": chats
        })

    def post(self, request):
        serializer = PatientChatCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat = create_or_get_patient_doctor_chat(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Chat opened successfully",
            "chat": chat
        }, status=201)


class PatientChatMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request, chat_id):
        messages = get_chat_messages(request.user, chat_id)

        return Response({
            "messages": messages
        })

    def post(self, request, chat_id):
        serializer = PatientMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = send_patient_chat_message(
            request.user,
            chat_id,
            serializer.validated_data
        )

        return Response({
            "message": "Message sent successfully",
            "data": message
        }, status=201)
    

class PatientSupportChatsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        chats = get_patient_support_chats(request.user)

        return Response({
            "support_chats": chats
        })

    def post(self, request):
        chat = create_or_get_patient_support_chat(request.user)

        return Response({
            "message": "Support chat opened successfully",
            "chat": chat
        }, status=201)


class PatientSupportChatMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request, chat_id):
        messages = get_support_chat_messages(request.user, chat_id)

        return Response({
            "messages": messages
        })

    def post(self, request, chat_id):
        serializer = PatientMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = send_patient_support_message(
            request.user,
            chat_id,
            serializer.validated_data
        )

        return Response({
            "message": "Support message sent successfully",
            "data": message
        }, status=201)
    
class PatientRatingsView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        ratings = get_patient_ratings(request.user)

        return Response({
            "ratings": ratings
        })

    def post(self, request):
        serializer = PatientRatingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating = create_patient_rating(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "Doctor rated successfully",
            "rating": rating
        }, status=201)
    

class PatientAiScansView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        scans = get_patient_ai_scans(request.user)

        return Response({
            "scans": scans
        })

    def post(self, request):
        serializer = PatientAiScanUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scan = create_patient_ai_scan(
            request.user,
            serializer.validated_data
        )

        return Response({
            "message": "AI scan uploaded successfully",
            "scan": scan
        }, status=201)


class PatientAiScanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request, scan_id):
        scan = get_patient_ai_scan_detail(
            request.user,
            scan_id
        )

        return Response(scan)