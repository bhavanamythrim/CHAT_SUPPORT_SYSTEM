from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from tickets.models import Ticket
from .assistant import create_bot_reply
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer


@login_required
def live_chat_view(request):
    room = (
        ChatRoom.objects
        .filter(participants=request.user, is_closed=False, ticket__isnull=True)
        .order_by("-created_at")
        .first()
    )

    if room is None:
        room = ChatRoom.objects.create(is_closed=False)
        room.participants.add(request.user)

    if room.messages.count() == 0:
        create_bot_reply(room=room, ticket=None, customer_message="hello")

    messages_qs = room.messages.select_related("sender").order_by("timestamp")

    return render(
        request,
        "chat/live_chat.html",
        {
            "room": room,
            "messages": messages_qs,
        },
    )


class CreateChatRoomView(generics.CreateAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        room = serializer.save()
        room.participants.add(self.request.user)


class ChatRoomListView(generics.ListAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(participants=self.request.user)


class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        room = serializer.validated_data['room']

        if self.request.user not in room.participants.all():
            raise PermissionDenied("You are not a participant of this room.")

        ticket = Ticket.objects.filter(chat_room=room).first()
        if room.is_closed or (ticket is not None and ticket.status == "closed"):
            raise PermissionDenied("This chat room is closed. Messages cannot be sent.")

        message = serializer.save(sender=self.request.user)

        if getattr(self.request.user, "role", "") == "CUSTOMER":
            create_bot_reply(room=room, ticket=ticket, customer_message=message.text)


class RoomMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = ChatRoom.objects.get(id=room_id)

        if self.request.user not in room.participants.all():
            raise PermissionDenied("You are not allowed to view this room.")

        return room.messages.all().order_by('timestamp')
