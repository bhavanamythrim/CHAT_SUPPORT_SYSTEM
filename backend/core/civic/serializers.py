from rest_framework import serializers

from .models import (
    ChatSession,
    Complaint,
    DocumentsRequired,
    KnowledgeBase,
    Message,
    Office,
    Service,
    ServiceUsageStat,
)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class OfficeSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Office
        fields = "__all__"


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBase
        fields = "__all__"


class DocumentsRequiredSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentsRequired
        fields = "__all__"


class ChatSessionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ChatSession
        fields = "__all__"
        read_only_fields = ("complaint_tracking_id", "last_message_at", "created_at", "updated_at")


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Message
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = "__all__"
        read_only_fields = ("tracking_id",)


class ServiceUsageStatSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = ServiceUsageStat
        fields = "__all__"


class ChatSendSerializer(serializers.Serializer):
    session = serializers.PrimaryKeyRelatedField(queryset=ChatSession.objects.all())
    content = serializers.CharField()
