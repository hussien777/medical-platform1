from rest_framework import serializers


class DoctorProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    gender = serializers.ChoiceField(
        choices=["male", "female"],
        required=False
    )

    age = serializers.IntegerField(min_value=23, required=False)

    university_name = serializers.CharField(required=False)
    graduation_year = serializers.IntegerField(required=False)
    years_of_experience = serializers.IntegerField(min_value=0, required=False)

    governorate_id = serializers.IntegerField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    clinic_name = serializers.CharField(required=False, allow_blank=True)

    certificate_image = serializers.ImageField(required=False)
    profile_image = serializers.ImageField(required=False)

    def validate_email(self, value):
        if not value.lower().endswith("@gmail.com"):
            raise serializers.ValidationError("Only Gmail allowed")
        return value

    def validate_certificate_image(self, value):
        if value and not value.name.lower().endswith((".jpg", ".jpeg")):
            raise serializers.ValidationError("Certificate image must be JPG")
        return value

    def validate_profile_image(self, value):
        if value and not value.name.lower().endswith((".jpg", ".jpeg")):
            raise serializers.ValidationError("Profile image must be JPG")
        return value
   

class DoctorAppointmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["pending", "confirmed", "cancelled"]
    )

class DoctorMessageCreateSerializer(serializers.Serializer):
    text_content = serializers.CharField()

class DoctorAiScanAnalysisUpdateSerializer(serializers.Serializer):
    ai_result = serializers.CharField()

