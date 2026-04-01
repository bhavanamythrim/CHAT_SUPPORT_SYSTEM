from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import NotificationPreference

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        validated_data['role'] = 'CUSTOMER'
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["sms", "email_digest", "in_app", "escalation"]
