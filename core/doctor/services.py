from datetime import date

from rest_framework.exceptions import ValidationError

from core.models import Doctor, User, Appointment, Chat, Message, SupportRequest, AiScan, Consultation

from django.utils import timezone

def model_has_field(model_instance, field_name):
    return any(field.name == field_name for field in model_instance._meta.fields)


def get_model_value(model_instance, field_name):
    if model_has_field(model_instance, field_name):
        value = getattr(model_instance, field_name)

        if value is None:
            return None

        # For image/file fields
        if hasattr(value, "url"):
            try:
                return value.url
            except Exception:
                return str(value)

        return value

    return None


def set_model_value(model_instance, field_name, value, update_fields):
    if model_has_field(model_instance, field_name):
        setattr(model_instance, field_name, value)
        update_fields.append(field_name)


def calculate_doctor_experience_limit(graduation_year):
    if not graduation_year:
        return None

    current_year = date.today().year
    return current_year - graduation_year


def get_doctor_profile(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    return {
        "user_id": user.user_id,
        "doctor_id": doctor.doctor_id,
        "full_name": user.full_name,
        "national_id": user.national_id,
        "email": user.email,
        "role": user.role,
        "account_status": user.account_status,

        "gender": doctor.gender,
        "age": doctor.age,
        "university_name": doctor.university_name,
        "graduation_year": doctor.graduation_year,
        "years_of_experience": doctor.years_of_experience,
        "certificate_image": get_model_value(doctor, "certificate_image"),
        "activation_status": doctor.activation_status,
        "average_rating": doctor.average_rating,

        # Optional fields, only returned if they exist in your Doctor model
        "governorate_id": get_model_value(doctor, "governorate_id"),
        "phone_number": (
            get_model_value(doctor, "phone_number")
            or get_model_value(doctor, "phone")
        ),
        "clinic_name": (
            get_model_value(doctor, "clinic_name")
            or get_model_value(doctor, "clinic")
        ),
        "profile_image": (
            get_model_value(doctor, "profile_image")
            or get_model_value(doctor, "photo")
        ),
    }


def update_doctor_profile(user, data):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    user_update_fields = []
    doctor_update_fields = []

    if "email" in data:
        email_exists = User.objects.filter(
            email=data["email"]
        ).exclude(
            user_id=user.user_id
        ).exists()

        if email_exists:
            raise ValidationError({"email": "Email already exists"})

        user.email = data["email"]
        user_update_fields.append("email")

    if "full_name" in data:
        user.full_name = data["full_name"]
        user_update_fields.append("full_name")

    if user_update_fields:
        user.save(update_fields=user_update_fields)

    if "gender" in data:
        doctor.gender = data["gender"]
        doctor_update_fields.append("gender")

    if "age" in data:
        doctor.age = data["age"]
        doctor_update_fields.append("age")

    if "university_name" in data:
        doctor.university_name = data["university_name"]
        doctor_update_fields.append("university_name")

    if "graduation_year" in data:
        doctor.graduation_year = data["graduation_year"]
        doctor_update_fields.append("graduation_year")

    if "years_of_experience" in data:
        graduation_year = data.get("graduation_year", doctor.graduation_year)
        max_experience = calculate_doctor_experience_limit(graduation_year)

        if max_experience is not None and data["years_of_experience"] > max_experience:
            raise ValidationError({
                "years_of_experience": "Experience years cannot be greater than years since graduation"
            })

        doctor.years_of_experience = data["years_of_experience"]
        doctor_update_fields.append("years_of_experience")

    if "certificate_image" in data:
        doctor.certificate_image = data["certificate_image"]
        doctor_update_fields.append("certificate_image")

    # Optional fields, updated only if they exist in your Doctor model
    if "governorate_id" in data:
        set_model_value(doctor, "governorate_id", data["governorate_id"], doctor_update_fields)

    if "phone_number" in data:
        if model_has_field(doctor, "phone_number"):
            set_model_value(doctor, "phone_number", data["phone_number"], doctor_update_fields)
        elif model_has_field(doctor, "phone"):
            set_model_value(doctor, "phone", data["phone_number"], doctor_update_fields)

    if "clinic_name" in data:
        if model_has_field(doctor, "clinic_name"):
            set_model_value(doctor, "clinic_name", data["clinic_name"], doctor_update_fields)
        elif model_has_field(doctor, "clinic"):
            set_model_value(doctor, "clinic", data["clinic_name"], doctor_update_fields)

    if "profile_image" in data:
        if model_has_field(doctor, "profile_image"):
            set_model_value(doctor, "profile_image", data["profile_image"], doctor_update_fields)
        elif model_has_field(doctor, "photo"):
            set_model_value(doctor, "photo", data["profile_image"], doctor_update_fields)

    if doctor_update_fields:
        doctor.save(update_fields=list(set(doctor_update_fields)))

    return get_doctor_profile(user)


def get_doctor_appointments(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related(
        "patient",
        "patient__user",
        "consultation"
    ).order_by("-appointment_datetime")

    result = []

    for appointment in appointments:
        result.append({
            "appointment_id": appointment.appointment_id,
            "consultation_id": appointment.consultation.consultation_id,
            "patient_id": appointment.patient.patient_id,
            "patient_name": appointment.patient.user.full_name,
            "patient_email": appointment.patient.user.email,
            "appointment_datetime": appointment.appointment_datetime,
            "status": appointment.status,
        })

    return result


def update_doctor_appointment_status(user, appointment_id, data):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    appointment = Appointment.objects.filter(
        appointment_id=appointment_id,
        doctor=doctor
    ).select_related(
        "consultation"
    ).first()

    if not appointment:
        raise ValidationError("Appointment not found")

    appointment.status = data["status"]
    appointment.save(update_fields=["status"])

    # Keep consultation status close to appointment status
    if appointment.consultation:
        if data["status"] == "confirmed":
            appointment.consultation.status = "accepted"
        elif data["status"] == "cancelled":
            appointment.consultation.status = "cancelled"
        else:
            appointment.consultation.status = "requested"

        appointment.consultation.save(update_fields=["status"])

    return {
        "appointment_id": appointment.appointment_id,
        "consultation_id": appointment.consultation.consultation_id,
        "patient_id": appointment.patient.patient_id,
        "patient_name": appointment.patient.user.full_name,
        "appointment_datetime": appointment.appointment_datetime,
        "status": appointment.status,
    }


def delete_doctor_appointment(user, appointment_id):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    appointment = Appointment.objects.filter(
        appointment_id=appointment_id,
        doctor=doctor
    ).first()

    if not appointment:
        raise ValidationError("Appointment not found")

    appointment.delete()

    return {
        "message": "Appointment deleted successfully",
        "appointment_id": appointment_id
    }

def get_doctor_chats(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    chats = Chat.objects.filter(
        consultation__doctor=doctor,
        chat_type="doctor"
    ).select_related(
        "consultation",
        "consultation__patient",
        "consultation__patient__user"
    ).order_by("-created_at")

    result = []

    for chat in chats:
        result.append(format_doctor_chat(chat))

    return result


def get_doctor_chat_messages(user, chat_id):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        consultation__doctor=doctor,
        chat_type="doctor"
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
            "text_content": message.text_content,
            "image_path": message.image_path,
            "created_at": message.created_at,
        })

    return result


def send_doctor_chat_message(user, chat_id, data):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    chat = Chat.objects.filter(
        chat_id=chat_id,
        consultation__doctor=doctor,
        chat_type="doctor",
        status="open"
    ).first()

    if not chat:
        raise ValidationError("Chat not found or closed")

    message = Message.objects.create(
        chat=chat,
        sender_user=user,
        message_type="text",
        text_content=data["text_content"]
    )

    return {
        "message_id": message.message_id,
        "chat_id": chat.chat_id,
        "sender_user_id": user.user_id,
        "sender_name": user.full_name,
        "sender_role": user.role,
        "message_type": message.message_type,
        "text_content": message.text_content,
        "image_path": message.image_path,
        "created_at": message.created_at,
    }


def format_doctor_chat(chat):
    return {
        "chat_id": chat.chat_id,
        "consultation_id": chat.consultation.consultation_id,
        "patient_id": chat.consultation.patient.patient_id,
        "patient_name": chat.consultation.patient.user.full_name,
        "patient_email": chat.consultation.patient.user.email,
        "chat_type": chat.chat_type,
        "status": chat.status,
        "created_at": chat.created_at,
    }

def create_or_get_doctor_support_chat(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

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
            return format_doctor_support_chat(chat, support_request)

    support_request = SupportRequest.objects.create(
        submitted_by_user=user,
        subject="Doctor Support Chat",
        description="Support chat opened by doctor",
        status="open"
    )

    chat = Chat.objects.create(
        support_id=support_request.support_id,
        chat_type="support",
        status="open"
    )

    return format_doctor_support_chat(chat, support_request)


def get_doctor_support_chats(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

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
            result.append(format_doctor_support_chat(chat, support_request))

    return result


def get_doctor_support_chat_messages(user, chat_id):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

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
            "text_content": message.text_content,
            "image_path": message.image_path,
            "created_at": message.created_at,
        })

    return result


def send_doctor_support_message(user, chat_id, data):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

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
        text_content=data["text_content"]
    )

    return {
        "message_id": message.message_id,
        "chat_id": chat.chat_id,
        "sender_user_id": user.user_id,
        "sender_name": user.full_name,
        "sender_role": user.role,
        "message_type": message.message_type,
        "text_content": message.text_content,
        "image_path": message.image_path,
        "created_at": message.created_at,
    }


def format_doctor_support_chat(chat, support_request):
    return {
        "chat_id": chat.chat_id,
        "support_id": support_request.support_id,
        "subject": support_request.subject,
        "support_status": support_request.status,
        "chat_type": chat.chat_type,
        "chat_status": chat.status,
        "created_at": chat.created_at,
    }

def get_doctor_dashboard_summary(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    total_appointments = Appointment.objects.filter(
        doctor=doctor
    ).count()

    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_datetime__gte=timezone.now()
    ).exclude(
        status="cancelled"
    ).count()

    pending_appointments = Appointment.objects.filter(
        doctor=doctor,
        status="pending"
    ).count()

    confirmed_appointments = Appointment.objects.filter(
        doctor=doctor,
        status="confirmed"
    ).count()

    cancelled_appointments = Appointment.objects.filter(
        doctor=doctor,
        status="cancelled"
    ).count()

    doctor_chats_count = Chat.objects.filter(
        consultation__doctor=doctor,
        chat_type="doctor"
    ).count()

    return {
        "profile": get_doctor_profile(user),
        "appointments": {
            "total": total_appointments,
            "upcoming": upcoming_appointments,
            "pending": pending_appointments,
            "confirmed": confirmed_appointments,
            "cancelled": cancelled_appointments,
        },
        "messages": {
            "doctor_chats": doctor_chats_count
        },
        "average_rating": doctor.average_rating,
    }


def format_doctor_ai_scan(scan):
    image_url = None

    if scan.uploaded_image:
        try:
            image_url = scan.uploaded_image.url
        except Exception:
            image_url = str(scan.uploaded_image)

    return {
        "scan_id": scan.scan_id,
        "patient_id": scan.patient.patient_id,
        "patient_name": scan.patient.user.full_name,
        "patient_email": scan.patient.user.email,
        "operation_number": scan.operation_number,
        "uploaded_image": image_url,
        "ai_result": scan.ai_result,
        "scan_datetime": scan.scan_datetime,
    }


def get_doctor_connected_patient_ids(doctor):
    return Consultation.objects.filter(
        doctor=doctor
    ).values_list(
        "patient_id",
        flat=True
    ).distinct()


def get_doctor_ai_scans(user):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    patient_ids = get_doctor_connected_patient_ids(doctor)

    scans = AiScan.objects.filter(
        patient_id__in=patient_ids
    ).select_related(
        "patient",
        "patient__user"
    ).order_by("-scan_datetime")

    return [
        format_doctor_ai_scan(scan) for scan in scans
    ]


def get_doctor_ai_scan_detail(user, scan_id):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    patient_ids = get_doctor_connected_patient_ids(doctor)

    scan = AiScan.objects.filter(
        scan_id=scan_id,
        patient_id__in=patient_ids
    ).select_related(
        "patient",
        "patient__user"
    ).first()

    if not scan:
        raise ValidationError("AI scan not found or you do not have access")

    return format_doctor_ai_scan(scan)


def update_doctor_ai_scan_analysis(user, scan_id, data):
    doctor = Doctor.objects.filter(user=user).first()

    if not doctor:
        raise ValidationError("Doctor profile not found")

    patient_ids = get_doctor_connected_patient_ids(doctor)

    scan = AiScan.objects.filter(
        scan_id=scan_id,
        patient_id__in=patient_ids
    ).select_related(
        "patient",
        "patient__user"
    ).first()

    if not scan:
        raise ValidationError("AI scan not found or you do not have access")

    scan.ai_result = data["ai_result"]
    scan.save(update_fields=["ai_result"])

    return format_doctor_ai_scan(scan)