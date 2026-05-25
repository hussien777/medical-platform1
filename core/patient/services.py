from datetime import date

from rest_framework.exceptions import ValidationError
from core.ai_model.client import send_scan_to_ai_model
from core.models import (
    Patient,
    User,
    Doctor,
    Consultation,
    Appointment,
    AiScan,
    Chat,
    Message,
    SupportRequest,
    Rating,
)
from django.db import transaction

from core.encryption import encrypt_message_text, decrypt_message_text

from django.utils import timezone

from django.db.models import Avg


def calculate_age(date_of_birth):
    if not date_of_birth:
        return None

    today = date.today()
    age = today.year - date_of_birth.year

    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1

    return age


def get_patient_profile(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "national_id": user.national_id,
        "email": user.email,
        "gender": patient.gender,
        "date_of_birth": patient.date_of_birth,
        "age": calculate_age(patient.date_of_birth),
        "governorate_id": patient.governorate_id,
    }


def update_patient_profile(user, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    if "email" in data:
        email_exists = User.objects.filter(email=data["email"]).exclude(user_id=user.user_id).exists()

        if email_exists:
            raise ValidationError({"email": "Email already exists"})

        user.email = data["email"]

    if "full_name" in data:
        user.full_name = data["full_name"]

    user.save(update_fields=["full_name", "email"])

    if "gender" in data:
        patient.gender = data["gender"]

    if "date_of_birth" in data:
        patient.date_of_birth = data["date_of_birth"]

    if "governorate_id" in data:
        patient.governorate_id = data["governorate_id"]

    patient.save(update_fields=["gender", "date_of_birth", "governorate_id"])

    return get_patient_profile(user)

def get_available_doctors():
    doctors = Doctor.objects.filter(
        activation_status="active",
        user__account_status="active",
        user__role="doctor"
    )

    result = []

    for doctor in doctors:
        result.append({
            "doctor_id": doctor.doctor_id,
            "user_id": doctor.user.user_id,
            "full_name": doctor.user.full_name,
            "email": doctor.user.email,
            "gender": doctor.gender,
            "age": doctor.age,
            "university": doctor.university_name,
            "graduation_year": doctor.graduation_year,
            "experience_years": doctor.years_of_experience,
            "average_rating": doctor.average_rating,
        })

    return result


@transaction.atomic
def create_patient_appointment(user, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    doctor = Doctor.objects.filter(
        doctor_id=data["doctor_id"],
        activation_status="active",
        user__account_status="active",
        user__role="doctor"
    ).first()

    if not doctor:
        raise ValidationError("Doctor not found or not active")

    appointment_datetime = data["appointment_datetime"]

    existing_appointment = Appointment.objects.filter(
        doctor=doctor,
        appointment_datetime=appointment_datetime
    ).first()

    if existing_appointment:
        raise ValidationError("This appointment time is already booked")

    consultation = Consultation.objects.create(
        patient=patient,
        doctor=doctor,
        status="requested"
    )

    appointment = Appointment.objects.create(
        consultation=consultation,
        patient=patient,
        doctor=doctor,
        appointment_datetime=appointment_datetime,
        status="pending"
    )

    return {
        "appointment_id": appointment.appointment_id,
        "consultation_id": consultation.consultation_id,
        "doctor_id": doctor.doctor_id,
        "doctor_name": doctor.user.full_name,
        "appointment_datetime": appointment.appointment_datetime,
        "status": appointment.status,
    }


def get_patient_appointments(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related(
        "doctor",
        "doctor__user",
        "consultation"
    ).order_by("-appointment_datetime")

    result = []

    for appointment in appointments:
        result.append({
            "appointment_id": appointment.appointment_id,
            "consultation_id": appointment.consultation.consultation_id,
            "doctor_id": appointment.doctor.doctor_id,
            "doctor_name": appointment.doctor.user.full_name,
            "appointment_datetime": appointment.appointment_datetime,
            "status": appointment.status,
        })

    return result


def get_patient_dashboard_summary(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    total_exams = AiScan.objects.filter(patient=patient).count()

    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_datetime__gte=timezone.now()
    ).count()

    return {
        "profile": get_patient_profile(user),
        "total_exams": total_exams,
        "upcoming_appointments": upcoming_appointments,
    }


@transaction.atomic
def create_or_get_patient_doctor_chat(user, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    doctor = Doctor.objects.filter(
        doctor_id=data["doctor_id"],
        activation_status="active",
        user__account_status="active",
        user__role="doctor"
    ).first()

    if not doctor:
        raise ValidationError("Doctor not found or not active")

    existing_chat = Chat.objects.filter(
        consultation__patient=patient,
        consultation__doctor=doctor,
        chat_type="doctor",
        status="open"
    ).select_related("consultation", "consultation__doctor", "consultation__doctor__user").first()

    if existing_chat:
        return format_chat(existing_chat)

    consultation = Consultation.objects.create(
        patient=patient,
        doctor=doctor,
        status="requested"
    )

    chat = Chat.objects.create(
        consultation=consultation,
        chat_type="doctor",
        status="open"
    )

    return format_chat(chat)


def get_patient_chats(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    chats = Chat.objects.filter(
        consultation__patient=patient,
        chat_type="doctor"
    ).select_related(
        "consultation",
        "consultation__doctor",
        "consultation__doctor__user"
    ).order_by("-created_at")

    return [format_chat(chat) for chat in chats]


def get_chat_messages(user, chat_id):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        consultation__patient=patient
    ).first()

    if not chat:
        raise ValidationError("Chat not found")

    messages = Message.objects.filter(
        chat=chat
    ).select_related(
        "sender_user"
    ).order_by("created_at")

    result = []

    for message in messages:
        result.append({
            "message_id": message.message_id,
            "chat_id": chat.chat_id,
            "sender_user_id": message.sender_user.user_id,
            "sender_name": message.sender_user.full_name,
            "sender_role": message.sender_user.role,
            "message_type": message.message_type,
            "text_content": decrypt_message_text(message.text_content),
            "image_path": message.image_path,
            "created_at": message.created_at,
        })

    return result


def send_patient_chat_message(user, chat_id, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        consultation__patient=patient,
        status="open"
    ).first()

    if not chat:
        raise ValidationError("Chat not found or closed")

    message = Message.objects.create(
        chat=chat,
        sender_user=user,
        message_type="text",
        text_content=encrypt_message_text(data["text_content"])
    )

    return {
        "message_id": message.message_id,
        "chat_id": chat.chat_id,
        "sender_user_id": user.user_id,
        "sender_name": user.full_name,
        "sender_role": user.role,
        "message_type": message.message_type,
        "text_content": decrypt_message_text(message.text_content),
        "image_path": message.image_path,
        "created_at": message.created_at,
    }


def format_chat(chat):
    return {
        "chat_id": chat.chat_id,
        "consultation_id": chat.consultation.consultation_id,
        "doctor_id": chat.consultation.doctor.doctor_id,
        "doctor_name": chat.consultation.doctor.user.full_name,
        "chat_type": chat.chat_type,
        "status": chat.status,
        "created_at": chat.created_at,
    }

@transaction.atomic
def create_or_get_patient_support_chat(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    support_request = SupportRequest.objects.filter(
        submitted_by_user=user,
        status="open"
    ).order_by("-created_at").first()

    if support_request:
        chat = Chat.objects.filter(
            support_id=support_request.support_id,
            chat_type="support",
            status="open"
        ).first()

        if chat:
            return format_support_chat(chat, support_request)

    support_request = SupportRequest.objects.create(
        submitted_by_user=user,
        subject="Patient Support Chat",
        description="Support chat opened by patient",
        status="open"
    )

    chat = Chat.objects.create(
        support_id=support_request.support_id,
        chat_type="support",
        status="open"
    )

    return format_support_chat(chat, support_request)


def get_patient_support_chats(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    support_requests = SupportRequest.objects.filter(
        submitted_by_user=user
    ).order_by("-created_at")

    result = []

    for support_request in support_requests:
        chat = Chat.objects.filter(
            support_id=support_request.support_id,
            chat_type="support"
        ).first()

        if chat:
            result.append(format_support_chat(chat, support_request))

    return result


def get_support_chat_messages(user, chat_id):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        chat_type="support"
    ).first()

    if not chat:
        raise ValidationError("Support chat not found")

    support_request = SupportRequest.objects.filter(
        support_id=chat.support_id,
        submitted_by_user=user
    ).first()

    if not support_request:
        raise ValidationError("You do not have access to this support chat")

    messages = Message.objects.filter(
        chat=chat
    ).select_related(
        "sender_user"
    ).order_by("created_at")

    result = []

    for message in messages:
        result.append({
            "message_id": message.message_id,
            "chat_id": chat.chat_id,
            "sender_user_id": message.sender_user.user_id,
            "sender_name": message.sender_user.full_name,
            "sender_role": message.sender_user.role,
            "message_type": message.message_type,
            "text_content": decrypt_message_text(message.text_content),
            "image_path": message.image_path,
            "created_at": message.created_at,
        })

    return result


def send_patient_support_message(user, chat_id, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        chat_type="support",
        status="open"
    ).first()

    if not chat:
        raise ValidationError("Support chat not found or closed")

    support_request = SupportRequest.objects.filter(
        support_id=chat.support_id,
        submitted_by_user=user
    ).first()

    if not support_request:
        raise ValidationError("You do not have access to this support chat")

    message = Message.objects.create(
        chat=chat,
        sender_user=user,
        message_type="text",
        text_content=encrypt_message_text(data["text_content"])
    )

    return {
        "message_id": message.message_id,
        "chat_id": chat.chat_id,
        "sender_user_id": user.user_id,
        "sender_name": user.full_name,
        "sender_role": user.role,
        "message_type": message.message_type,
        "text_content": decrypt_message_text(message.text_content),
        "image_path": message.image_path,
        "created_at": message.created_at,
    }


def format_support_chat(chat, support_request):
    return {
        "chat_id": chat.chat_id,
        "support_id": support_request.support_id,
        "subject": support_request.subject,
        "support_status": support_request.status,
        "chat_type": chat.chat_type,
        "chat_status": chat.status,
        "created_at": chat.created_at,
    }

@transaction.atomic
def create_patient_rating(user, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    doctor = Doctor.objects.filter(
        doctor_id=data["doctor_id"],
        activation_status="active",
        user__account_status="active",
        user__role="doctor"
    ).first()

    if not doctor:
        raise ValidationError("Doctor not found or not active")

    stars = data["stars"]
    comment = data.get("comment", "")

    consultation = Consultation.objects.filter(
        patient=patient,
        doctor=doctor
    ).order_by("-consultation_id").first()

    if not consultation:
        consultation = Consultation.objects.create(
            patient=patient,
            doctor=doctor,
            status="requested"
        )

    existing_rating = Rating.objects.filter(
        giver_user=user,
        receiver_user=doctor.user
    ).first()

    if existing_rating:
        existing_rating.stars = stars
        existing_rating.comment = comment
        existing_rating.consultation = consultation
        existing_rating.save(update_fields=["stars", "comment", "consultation"])
        rating = existing_rating
    else:
        rating = Rating.objects.create(
            consultation=consultation,
            giver_user=user,
            receiver_user=doctor.user,
            stars=stars,
            comment=comment
        )

    average_rating = Rating.objects.filter(
        receiver_user=doctor.user
    ).aggregate(
        average=Avg("stars")
    )["average"] or 0

    doctor.average_rating = round(float(average_rating), 1)
    doctor.save(update_fields=["average_rating"])

    return {
        "rating_id": rating.rating_id,
        "doctor_id": doctor.doctor_id,
        "doctor_name": doctor.user.full_name,
        "patient_id": patient.patient_id,
        "stars": rating.stars,
        "comment": rating.comment,
        "doctor_average_rating": doctor.average_rating,
        "rated_at": rating.rated_at,
    }


def get_patient_ratings(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    ratings = Rating.objects.filter(
        giver_user=user
    ).select_related(
        "receiver_user"
    ).order_by("-rated_at")

    result = []

    for rating in ratings:
        doctor = Doctor.objects.filter(user=rating.receiver_user).first()

        result.append({
            "rating_id": rating.rating_id,
            "doctor_id": doctor.doctor_id if doctor else None,
            "doctor_name": rating.receiver_user.full_name,
            "stars": rating.stars,
            "comment": rating.comment,
            "doctor_average_rating": doctor.average_rating if doctor else None,
            "rated_at": rating.rated_at,
        })

    return result


def get_patient_ratings(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    ratings = Rating.objects.filter(
        giver_user=user
    ).select_related(
        "receiver_user"
    ).order_by("-rated_at")

    result = []

    for rating in ratings:
        doctor = Doctor.objects.filter(user=rating.receiver_user).first()

        result.append({
            "rating_id": rating.rating_id,
            "doctor_id": doctor.doctor_id if doctor else None,
            "doctor_name": rating.receiver_user.full_name,
            "stars": rating.stars,
            "comment": rating.comment,
            "doctor_average_rating": doctor.average_rating if doctor else None,
            "rated_at": rating.rated_at,
        })

    return result


def generate_scan_operation_number(patient):
    field = AiScan._meta.get_field("operation_number")
    field_type = field.get_internal_type()

    timestamp_number = int(timezone.now().strftime("%Y%m%d%H%M%S"))

    if field_type in ["IntegerField", "BigIntegerField", "PositiveIntegerField", "PositiveBigIntegerField"]:
        return timestamp_number

    return f"SCAN-{patient.patient_id}-{timestamp_number}"


def format_patient_ai_scan(scan):
    image_url = None

    if scan.uploaded_image:
        try:
            image_url = scan.uploaded_image.url
        except Exception:
            image_url = str(scan.uploaded_image)

    return {
        "scan_id": scan.scan_id,
        "patient_id": scan.patient.patient_id,
        "operation_number": scan.operation_number,
        "uploaded_image": image_url,
        "ai_result": scan.ai_result,
        "scan_datetime": scan.scan_datetime,
    }


def create_patient_ai_scan(user, data):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    operation_number = generate_scan_operation_number(patient)

    uploaded_image = data["uploaded_image"]

    # Send the uploaded image to the external AI model API.
    # Django receives the file as "uploaded_image",
    # but the AI API receives it as "file" inside client.py.
    ai_response = send_scan_to_ai_model(uploaded_image)

    ai_result = ai_response.get(
        "ai_result",
        "AI analysis failed: No result returned from AI model."
    )

    # Reset file pointer after sending it to the AI API.
    # This protects file saving if uploaded_image is handled as a real file object.
    try:
        uploaded_image.seek(0)
    except Exception:
        pass

    scan = AiScan.objects.create(
        patient=patient,
        operation_number=operation_number,
        uploaded_image=uploaded_image,
        ai_result=ai_result
    )

    return format_patient_ai_scan(scan)


def get_patient_ai_scans(user):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    scans = AiScan.objects.filter(
        patient=patient
    ).order_by("-scan_datetime")

    return [
        format_patient_ai_scan(scan) for scan in scans
    ]


def get_patient_ai_scan_detail(user, scan_id):
    patient = Patient.objects.filter(user=user).first()

    if not patient:
        raise ValidationError("Patient profile not found")

    scan = AiScan.objects.filter(
        scan_id=scan_id,
        patient=patient
    ).first()

    if not scan:
        raise ValidationError("AI scan not found")

    return format_patient_ai_scan(scan)