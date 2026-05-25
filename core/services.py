from datetime import timedelta
import random
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError
from core.models import User, VerificationCode, Doctor, Patient, PasswordReset


#Expiration time for OTP code 
def is_expired(expires_at):
    now = timezone.now()

    if timezone.is_naive(expires_at):
        now = timezone.make_naive(now)

    return expires_at < now


#Welcome messages and OTP code 
def send_otp_email(email, otp, role):
    subject = "Eye Care Verification Code"

    message = (
        f"Welcome to Eye Care Medical Platform.\n\n"
        f"Your {role} verification code is: {otp}\n\n"
        f"This code will expire in 1 minute.\n"
        f"Do not share this code with anyone."
    )

    send_mail(
        subject,
        message,
        None,
        [email],
        fail_silently=False,
    )

# =========================
# CLEANUP EXPIRED PENDING REGISTRATIONS
# =========================
@transaction.atomic
def cleanup_expired_pending_registrations():
    now = timezone.now()

    expired_codes = VerificationCode.objects.filter(
        is_used=False,
        expires_at__lt=now,
        purpose__in=["PATIENT_REGISTER", "DOCTOR_REGISTER"],
        user__account_status="pending",
    ).select_related("user")

    deleted_count = 0
    processed_user_ids = set()

    for code_record in expired_codes:
        user = code_record.user

        if not user:
            continue

        if user.user_id in processed_user_ids:
            continue

        processed_user_ids.add(user.user_id)

        # Safety: never delete active users
        if user.account_status != "pending":
            continue

        # Delete role-specific profile first
        Patient.objects.filter(user=user).delete()
        Doctor.objects.filter(user=user).delete()

        # Delete all verification codes for this pending user
        VerificationCode.objects.filter(user=user).delete()

        # Delete user account
        user.delete()

        deleted_count += 1

    return deleted_count


# =========================
# REGISTER PATIENT
# =========================
@transaction.atomic
def register_patient(data):

    user = User.objects.create(
        full_name=data["full_name"],
        national_id=data["national_id"],
        email=data["email"],
        password_hash=make_password(data["password"]),
        role="patient",
        account_status="pending",
        created_at=timezone.now()
    )

    Patient.objects.create(
        user=user,
        date_of_birth=data.get("date_of_birth"),
        gender=data.get("gender")
    )

    create_patient_otp(user)

    return user

# =========================
# PATIENT OTP GENERATION
# =========================
def create_patient_otp(user):

    VerificationCode.objects.filter(
        user_id=user.user_id,
        purpose="PATIENT_REGISTER",
        is_used=False
    ).update(is_used=True)

    otp = str(random.randint(100000, 999999))

    VerificationCode.objects.create(
        user_id=user.user_id,
        code=otp,
        purpose="PATIENT_REGISTER",
        expires_at=timezone.now() + timedelta(minutes=1),
        is_used=False,
        created_at=timezone.now()
    )

    send_otp_email(user.email, otp, "patient")
    #print("PATIENT OTP:", otp)#remove them later beacuse we need them now to make sure the output otp code= sent otp code 

    return otp
    

# =========================
# DELETE PENDING ACCOUNT AFTER EXPIRED OTP
# =========================
@transaction.atomic
def delete_pending_registration_account(user):
    if not user:
        return

    # Safety: never delete active accounts
    if user.account_status != "pending":
        return

    # Delete role-specific profile first
    Patient.objects.filter(user=user).delete()
    Doctor.objects.filter(user=user).delete()

    # Delete all verification codes for this user
    VerificationCode.objects.filter(user=user).delete()

    # Delete the user account
    user.delete()




# =========================
# VERIFY PATIENT OTP
# =========================
def verify_patient_otp(data):

    user = User.objects.filter(
        email=data["email"],
        role="patient"
    ).first()

    if not user:
        raise ValidationError("User with this email does not exist")

    otp_record = VerificationCode.objects.filter(
        user_id=user.user_id,
        purpose="PATIENT_REGISTER",
        is_used=False
    ).order_by("-created_at").first()

    if not otp_record:
        raise ValidationError("Invalid OTP")

    if is_expired(otp_record.expires_at):
        delete_pending_registration_account(user)
        raise ValidationError("OTP expired. Pending patient account was deleted. Please register again.")

    if otp_record.code != data["otp_code"]:
        raise ValidationError("Invalid OTP")

    user.account_status = "active"
    user.save(update_fields=["account_status"])

    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])

    return user

# =========================
# REGISTER DOCTOR
# =========================
@transaction.atomic
def register_doctor(data):

    user = User.objects.create(
        full_name=data["full_name"],
        national_id=data["national_id"],
        email=data["email"],
        password_hash=make_password(data["password"]),
        role="doctor",
        account_status="pending",
        created_at=timezone.now()
    )

    # Create doctor profile
    Doctor.objects.create(
        user=user,
        gender=data["gender"],
        age=data["age"],
        university_name=data["university"],
        graduation_year=data["graduation_year"],
        years_of_experience=data["experience_years"],
        certificate_image=data["certificate_image"],
        activation_status="pending"
    )

    # Generate OTP
    create_doctor_otp(user)

    return user


# =========================
# DOCTOR OTP GENERATION
# =========================
def create_doctor_otp(user):

    VerificationCode.objects.filter(
        user_id=user.user_id,
        purpose="DOCTOR_REGISTER",
        is_used=False
    ).update(is_used=True)

    otp = str(random.randint(100000, 999999))

    VerificationCode.objects.create(
        user_id=user.user_id,
        code=otp,
        purpose="DOCTOR_REGISTER",
        expires_at=timezone.now() + timedelta(minutes=1),
        is_used=False,
        created_at=timezone.now()
    )

    send_otp_email(user.email, otp, "doctor")
    #print("DOCTOR OTP:", otp)


    return otp


# =========================
# VERIFY DOCTOR OTP
# =========================
def verify_doctor_otp(data):

    user = User.objects.filter(
        email=data["email"],
        role="doctor"
    ).first()

    if not user:
        raise ValidationError("Doctor not found")

    otp_record = VerificationCode.objects.filter(
        user_id=user.user_id,
        purpose="DOCTOR_REGISTER",
        is_used=False
    ).order_by("-created_at").first()

    if not otp_record:
        raise ValidationError("Invalid OTP")

    if is_expired(otp_record.expires_at):
        delete_pending_registration_account(user)
        raise ValidationError("OTP expired. Pending doctor account was deleted. Please register again.")

    if otp_record.code != data["otp_code"]:
        raise ValidationError("Invalid OTP")

    user.account_status = "active"
    user.save(update_fields=["account_status"])

    doctor = Doctor.objects.filter(user=user).first()

    if doctor:
        doctor.activation_status = "active"
        doctor.activated_at = timezone.now()
        doctor.save(update_fields=["activation_status", "activated_at"])

    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])

    return user



# =========================
# PASSWORD RESET REQUEST
# =========================
def request_password_reset(data):
    email = data["email"]

    user = User.objects.filter(email=email).first()

    if not user:
        raise ValidationError("No account found with this email address")

    PasswordReset.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)

    reset_code = str(random.randint(100000, 999999))

    PasswordReset.objects.create(
        user=user,
        reset_code=reset_code,
        expires_at=timezone.now() + timedelta(minutes=10),
        is_used=False
    )

    send_mail(
        subject="Eye Care Password Reset Code",
        message=f"Your password reset code is: {reset_code}\nThis code will expire in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return {
        "message": "Password reset code sent successfully."
    }


# =========================
# PASSWORD RESET CONFIRM
# =========================
def confirm_password_reset(data):
    email = data["email"]
    otp_code = data["otp_code"]
    new_password = data["new_password"]

    user = User.objects.filter(email=email).first()

    if not user:
        raise ValidationError("No account found with this email address")

    reset_record = PasswordReset.objects.filter(
        user=user,
        reset_code=otp_code,
        is_used=False
    ).order_by("-created_at").first()

    if not reset_record:
        raise ValidationError("Invalid reset code")

    if is_expired(reset_record.expires_at):
        raise ValidationError("Reset code expired")

    user.password_hash = make_password(new_password)
    user.save(update_fields=["password_hash"])

    reset_record.is_used = True
    reset_record.save(update_fields=["is_used"])

    return {
        "message": "Password reset successfully."
    }