from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from django.utils import timezone
from core.encryption import encrypt_message_text, decrypt_message_text
from rest_framework.exceptions import ValidationError

from core.models import User, Patient, Doctor, Admin, Chat, Message, SupportRequest

def get_admin_profile(user):
    if user.role != "admin":
        raise ValidationError("Admin access only")

    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "national_id": user.national_id,
        "email": user.email,
        "role": user.role,
        "account_status": user.account_status,
    }


def update_admin_profile(user, data):
    if user.role != "admin":
        raise ValidationError("Admin access only")

    update_fields = []

    if "full_name" in data:
        user.full_name = data["full_name"]
        update_fields.append("full_name")

    if "email" in data:
        email_exists = User.objects.filter(
            email=data["email"]
        ).exclude(
            user_id=user.user_id
        ).exists()

        if email_exists:
            raise ValidationError({
                "email": "Email already exists"
            })

        user.email = data["email"]
        update_fields.append("email")

    if update_fields:
        user.save(update_fields=update_fields)

    return get_admin_profile(user)


def get_admin_dashboard_summary(user):
    if user.role != "admin":
        raise ValidationError("Admin access only")

    total_users = User.objects.count()
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_admins = Admin.objects.count()

    pending_doctor_requests = Doctor.objects.filter(
        Q(activation_status="pending") |
        Q(user__account_status="pending")
    ).count()

    active_doctors = Doctor.objects.filter(
        activation_status="active",
        user__account_status="active"
    ).count()

    active_patients = Patient.objects.filter(
        user__account_status="active"
    ).count()

    return {
        "admin": get_admin_profile(user),
        "users": {
            "total": total_users,
            "patients": total_patients,
            "doctors": total_doctors,
            "admins": total_admins,
        },
        "doctors": {
            "pending_requests": pending_doctor_requests,
            "active": active_doctors,
        },
        "patients": {
            "active": active_patients,
        }
    }


def admin_has_access(user):
    if user.role != "admin":
        raise ValidationError("Admin access only")


def doctor_has_field(field_name):
    return any(field.name == field_name for field in Doctor._meta.fields)


def format_admin_doctor(doctor):
    return {
        "doctor_id": doctor.doctor_id,
        "user_id": doctor.user.user_id,
        "full_name": doctor.user.full_name,
        "national_id": doctor.user.national_id,
        "email": doctor.user.email,
        "account_status": doctor.user.account_status,

        "gender": doctor.gender,
        "age": doctor.age,
        "university_name": doctor.university_name,
        "graduation_year": doctor.graduation_year,
        "years_of_experience": doctor.years_of_experience,
        "certificate_image": doctor.certificate_image.url if doctor.certificate_image else None,
        "activation_status": doctor.activation_status,
        "average_rating": doctor.average_rating,
        "created_at": doctor.user.created_at,
    }


def get_admin_doctors(user):
    admin_has_access(user)

    pending_doctors = Doctor.objects.filter(
        Q(activation_status="pending") |
        Q(user__account_status="pending")
    ).select_related("user").order_by("-doctor_id")

    active_doctors = Doctor.objects.filter(
        activation_status="active",
        user__account_status="active"
    ).select_related("user").order_by("-doctor_id")

    return {
        "pending_doctors": [
            format_admin_doctor(doctor) for doctor in pending_doctors
        ],
        "active_doctors": [
            format_admin_doctor(doctor) for doctor in active_doctors
        ],
    }


@transaction.atomic
def approve_admin_doctor(user, doctor_id):
    admin_has_access(user)

    doctor = Doctor.objects.filter(
        doctor_id=doctor_id
    ).select_related("user").first()

    if not doctor:
        raise ValidationError("Doctor not found")

    doctor.activation_status = "active"
    doctor.user.account_status = "active"

    doctor_update_fields = ["activation_status"]

    if doctor_has_field("activated_at"):
        doctor.activated_at = timezone.now()
        doctor_update_fields.append("activated_at")

    doctor.save(update_fields=doctor_update_fields)
    doctor.user.save(update_fields=["account_status"])

    return format_admin_doctor(doctor)


@transaction.atomic
def delete_admin_doctor(user, doctor_id):
    admin_has_access(user)

    doctor = Doctor.objects.filter(
        doctor_id=doctor_id
    ).select_related("user").first()

    if not doctor:
        raise ValidationError("Doctor not found")

    doctor_data = format_admin_doctor(doctor)
    doctor_user = doctor.user

    try:
        doctor.delete()
        doctor_user.delete()
    except (ProtectedError, IntegrityError):
        raise ValidationError(
            "Cannot delete this doctor because related records exist"
        )

    return {
        "message": "Doctor deleted successfully",
        "doctor": doctor_data
    }

def format_admin_patient(patient):
    return {
        "patient_id": patient.patient_id,
        "user_id": patient.user.user_id,
        "full_name": patient.user.full_name,
        "national_id": patient.user.national_id,
        "email": patient.user.email,
        "account_status": patient.user.account_status,
        "gender": patient.gender,
        "date_of_birth": patient.date_of_birth,
        "governorate_id": patient.governorate_id,
        "created_at": patient.user.created_at,
    }


def get_admin_patients(user):
    admin_has_access(user)

    patients = Patient.objects.select_related(
        "user"
    ).order_by("-patient_id")

    return {
        "patients": [
            format_admin_patient(patient) for patient in patients
        ]
    }


@transaction.atomic
def delete_admin_patient(user, patient_id):
    admin_has_access(user)

    patient = Patient.objects.filter(
        patient_id=patient_id
    ).select_related("user").first()

    if not patient:
        raise ValidationError("Patient not found")

    patient_data = format_admin_patient(patient)
    patient_user = patient.user

    try:
        patient.delete()
        patient_user.delete()
    except (ProtectedError, IntegrityError):
        raise ValidationError(
            "Cannot delete this patient because related records exist"
        )

    return {
        "message": "Patient deleted successfully",
        "patient": patient_data
    }

def format_admin_support_chat(chat, support_request):
    requester = support_request.submitted_by_user

    return {
        "chat_id": chat.chat_id,
        "support_id": support_request.support_id,
        "subject": support_request.subject,
        "description": support_request.description,
        "support_status": support_request.status,

        "requester_user_id": requester.user_id,
        "requester_name": requester.full_name,
        "requester_email": requester.email,
        "requester_role": requester.role,

        "chat_type": chat.chat_type,
        "chat_status": chat.status,
        "created_at": chat.created_at,
    }


def get_admin_support_chats(user):
    admin_has_access(user)

    chats = Chat.objects.filter(
        chat_type="support"
    ).order_by("-created_at")

    result = []

    for chat in chats:
        support_request = SupportRequest.objects.filter(
            support_id=chat.support_id
        ).select_related(
            "submitted_by_user"
        ).first()

        if support_request:
            result.append(
                format_admin_support_chat(chat, support_request)
            )

    return {
        "support_chats": result
    }


def get_admin_support_chat_messages(user, chat_id):
    admin_has_access(user)

    chat = Chat.objects.filter(
        chat_id=chat_id,
        chat_type="support"
    ).first()

    if not chat:
        raise ValidationError("Support chat not found")

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

    return {
        "messages": result
    }


def send_admin_support_message(user, chat_id, data):
    admin_has_access(user)

    chat = Chat.objects.filter(
        chat_id=chat_id,
        chat_type="support",
        status="open"
    ).first()

    if not chat:
        raise ValidationError("Support chat not found or closed")

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