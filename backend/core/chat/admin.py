from django.contrib import admin

from .models import ChatRoom, KnowledgeEntry, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("sender", "text", "is_read", "timestamp")
    readonly_fields = ("timestamp",)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "is_closed", "participant_count", "created_at")
    list_filter = ("is_closed", "created_at")
    search_fields = ("id", "participants__username")
    filter_horizontal = ("participants",)
    readonly_fields = ("created_at",)
    inlines = (MessageInline,)

    @admin.display(description="Participants")
    def participant_count(self, obj):
        return obj.participants.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "short_text", "is_read", "timestamp")
    list_filter = ("is_read", "timestamp")
    search_fields = ("text", "sender__username", "room__id")
    autocomplete_fields = ("room", "sender")
    readonly_fields = ("timestamp",)

    @admin.display(description="Message")
    def short_text(self, obj):
        if len(obj.text) <= 60:
            return obj.text
        return f"{obj.text[:57]}..."


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "department", "intent", "question", "priority", "is_active", "updated_at")
    list_filter = ("department", "intent", "is_active")
    search_fields = ("question", "answer", "trigger_keywords")
    list_editable = ("priority", "is_active")
    ordering = ("priority", "id")
