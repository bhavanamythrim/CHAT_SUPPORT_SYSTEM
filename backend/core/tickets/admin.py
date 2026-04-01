from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "department",
        "status",
        "created_by",
        "assigned_to",
        "room_state",
        "created_at",
    )
    list_filter = ("department", "status", "created_at", "assigned_to")
    search_fields = (
        "title",
        "description",
        "created_by__username",
        "assigned_to__username",
    )
    autocomplete_fields = ("created_by", "assigned_to", "chat_room")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    actions = ("mark_open", "mark_in_progress", "mark_closed")

    @admin.display(description="Chat Room")
    def room_state(self, obj):
        if not obj.chat_room:
            return "No room"
        return "Closed" if obj.chat_room.is_closed else "Open"

    @admin.action(description="Mark selected tickets as Open")
    def mark_open(self, request, queryset):
        for ticket in queryset:
            ticket.status = "open"
            ticket.save(update_fields=["status"])

    @admin.action(description="Mark selected tickets as In Progress")
    def mark_in_progress(self, request, queryset):
        for ticket in queryset:
            ticket.status = "in_progress"
            ticket.save(update_fields=["status"])

    @admin.action(description="Mark selected tickets as Closed")
    def mark_closed(self, request, queryset):
        for ticket in queryset:
            ticket.status = "closed"
            ticket.save(update_fields=["status"])
