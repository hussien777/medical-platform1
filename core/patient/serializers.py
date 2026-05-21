from rest_framework import serializers

#The serializer is only for checking profile update data later.
class PatientProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    gender = serializers.ChoiceField(
        choices=["male", "female"],
        required=False
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    governorate_id = serializers.IntegerField(required=False, allow_null=True)
    email = serializers.EmailField(required=False)


class PatientAppointmentCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    appointment_datetime = serializers.DateTimeField()

class PatientChatCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()


class PatientMessageCreateSerializer(serializers.Serializer):
    text_content = serializers.CharField()


class PatientSupportMessageCreateSerializer(serializers.Serializer):
    text_content = serializers.CharField()


class PatientRatingCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    stars = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)


class PatientAiScanUploadSerializer(serializers.Serializer):
    uploaded_image = serializers.ImageField()

    def validate_uploaded_image(self, value):
        allowed_extensions = (".jpg", ".jpeg", ".png")

        if not value.name.lower().endswith(allowed_extensions):
            raise serializers.ValidationError(
                "Eye scan image must be JPG, JPEG, or PNG"
            )

        return value