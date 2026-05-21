from rest_framework import serializers


class AdminProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate_full_name(self, value):
        parts = value.strip().split()

        if len(parts) != 4:
            raise serializers.ValidationError(
                "Full name must consist of 4 parts"
            )

        return value
    
class AdminMessageCreateSerializer(serializers.Serializer):
    text_content = serializers.CharField()