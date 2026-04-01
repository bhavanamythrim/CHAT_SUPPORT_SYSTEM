from django.contrib import admin

from .models import ChatLog, ChatSession, Complaint, DocumentsRequired, KnowledgeBase, Message, Office, Service, ServiceUsageStat


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    list_editable = ("is_active",)
    ordering = ("name",)


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "service", "city", "timings", "is_active")
    list_filter = ("service", "city", "is_active")
    search_fields = ("name", "address", "contact_phone")


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "language", "question", "priority", "is_active")
    list_filter = ("service", "language", "is_active", "priority")
    search_fields = ("question", "answer", "keywords")
    list_editable = ("priority", "is_active")
    list_select_related = ("service",)
    autocomplete_fields = ("service",)
    ordering = ("service__name", "language", "priority", "id")
    list_per_page = 30


@admin.register(DocumentsRequired)
class DocumentsRequiredAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "title", "language", "is_active")
    list_filter = ("service", "language", "is_active")
    search_fields = ("title", "details")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "service", "status", "language_preference", "assigned_agent", "complaint_tracking_id", "last_message_at")
    list_filter = ("status", "language_preference", "service")
    search_fields = ("user__username", "complaint_tracking_id")
    autocomplete_fields = ("user", "assigned_agent", "service")
    inlines = (MessageInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sender", "sender_role", "language", "is_from_ai", "created_at")
    list_filter = ("sender_role", "language", "is_from_ai")
    search_fields = ("content", "sender__username")
    autocomplete_fields = ("session", "sender")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("id", "tracking_id", "service", "status", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "service")
    search_fields = ("tracking_id", "title", "description")
    autocomplete_fields = ("session", "service", "created_by", "assigned_to")


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("session__id",)
    autocomplete_fields = ("session", "message")


@admin.register(ServiceUsageStat)
class ServiceUsageStatAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "date", "total_queries", "escalated_queries", "complaints_raised")
    list_filter = ("date", "service")
    search_fields = ("service__name",)
