from rest_framework import serializers
from core.models import User


# =========================
# PATIENT REGISTRATION
# =========================
class PatientRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    national_id = serializers.RegexField(
        regex=r"^\d{10}$",
        error_messages={"invalid": "National ID must be exactly 10 digits"}
    )
    email = serializers.EmailField()
    
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=["male", "female"],
        required=False
    )

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):

        password = data.get("password")
        confirm_password = data.get("confirm_password")

        errors = {}

        if password != confirm_password:
            errors["password"] = "Passwords do not match"

        if password and len(password) < 8:
            errors["password"] = "Password must be at least 8 characters"
        
        if not data["email"].lower().endswith("@gmail.com"):
            errors["email"] = "Only Gmail allowed"

        if User.objects.filter(national_id=data["national_id"]).exists():
            errors["national_id"] = "National ID already exists"

        if User.objects.filter(email=data["email"]).exists():
            errors["email"] = "Email already exists"

        if errors:
            raise serializers.ValidationError(errors)

        return data


# =========================
# OTP VERIFICATION
# =========================
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField()


# =========================
# DOCTOR REGISTRATION
# =========================
class DoctorRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    national_id = serializers.RegexField(
        regex=r"^\d{10}$",
        error_messages={"invalid": "National ID must be exactly 10 digits"}
    )
    email = serializers.EmailField()

    gender = serializers.ChoiceField(choices=["male", "female"])
    age = serializers.IntegerField(min_value=23)

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    university = serializers.CharField()
    graduation_year = serializers.IntegerField()
    experience_years = serializers.IntegerField(min_value=0)

    certificate_image = serializers.ImageField()

    def validate(self, data):
        
        errors = {}
        
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            errors["password"] = "Passwords do not match"

        if password and len(password) < 8:
            errors["password"] = "Password must be at least 8 characters"

        if not data["email"].lower().endswith("@gmail.com"):
            errors["email"] = "Only Gmail allowed"

        certificate_image = data.get("certificate_image")
        if certificate_image and not certificate_image.name.lower().endswith((".jpg", ".jpeg")):
            errors["certificate_image"] = "Certificate image must be JPG"

        if User.objects.filter(national_id=data["national_id"]).exists():
            errors["national_id"] = "National ID already exists"

        if User.objects.filter(email=data["email"]).exists():
            errors["email"] = "Email already exists"

        if errors:
            raise serializers.ValidationError(errors)

        return data



# =========================
# PASSWORD RESET REQUEST
# =========================
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


# =========================
# PASSWORD RESET CONFIRM
# =========================
class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        errors = {}

        if new_password != confirm_password:
            errors["password"] = "Passwords do not match"

        if new_password and len(new_password) < 8:
            errors["password"] = "Password must be at least 8 characters"

        if errors:
            raise serializers.ValidationError(errors)

        return data