from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Count, Q
from rest_framework import generics, permissions

from chat.models import ChatRoom, Message
from chat.assistant import create_bot_reply
from .models import Ticket
from .serializers import TicketSerializer


class TicketListCreateView(generics.ListCreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


def _is_support_user(user):
    return user.is_staff or user.is_superuser or getattr(user, "role", "") == "ADMIN"


def _room_is_effectively_closed(room):
    ticket = getattr(room, "ticket", None)
    return room.is_closed or (ticket is not None and ticket.status == "closed")


@login_required
def ticket_list_view(request):
    if _is_support_user(request.user):
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(chat_room__participants=request.user)

    tickets = tickets.annotate(
        unread_count=Count(
            "chat_room__messages",
            filter=Q(chat_room__messages__is_read=False)
            & ~Q(chat_room__messages__sender=request.user),
        )
    ).order_by("-created_at")

    return render(request, "tickets/ticket_list.html", {"tickets": tickets})


@login_required
def create_ticket_view(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        department = request.POST.get("department") or "general"

        Ticket.objects.create(
            title=title,
            description=description,
            department=department,
            created_by=request.user,
        )

        return redirect("ticket-list-view")

    return render(request, "tickets/create_ticket.html")


@login_required
def ticket_chat_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    room = ticket.chat_room

    if room is None:
        return HttpResponseForbidden("Chat room not available")

    is_participant = room.participants.filter(id=request.user.id).exists()
    is_support = _is_support_user(request.user)

    if not is_participant and not is_support:
        return HttpResponseForbidden("Not allowed")

    if is_support and not is_participant:
        room.participants.add(request.user)

    if ticket.status == "closed" and not room.is_closed:
        room.is_closed = True
        room.save(update_fields=["is_closed"])

    messages_qs = Message.objects.filter(room=room).order_by("timestamp")

    Message.objects.filter(room=room, is_read=False).exclude(sender=request.user).update(is_read=True)

    return render(
        request,
        "tickets/ticket_chat.html",
        {
            "ticket": ticket,
            "room": room,
            "messages": messages_qs,
            "is_chat_closed": _room_is_effectively_closed(room),
        },
    )


@login_required
def send_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    is_participant = room.participants.filter(id=request.user.id).exists()
    is_support = _is_support_user(request.user)

    if not is_participant and not is_support:
        return HttpResponseForbidden("Not allowed")

    if is_support and not is_participant:
        room.participants.add(request.user)

    if _room_is_effectively_closed(room):
        messages.error(request, "This chat room is closed. You cannot send new messages.")
        return redirect(request.META.get("HTTP_REFERER", "ticket-list-view"))

    text = request.POST.get("message")
    if text:
        ticket = getattr(room, "ticket", None)
        Message.objects.create(
            room=room,
            sender=request.user,
            text=text,
        )

        if ticket and getattr(request.user, "role", "") == "CUSTOMER":
            create_bot_reply(room=room, ticket=ticket, customer_message=text)

    return redirect(request.META.get("HTTP_REFERER", "ticket-list-view"))
