import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from tickets.models import Ticket
from .assistant import create_bot_reply
from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        room = await self._get_room()
        if room is None:
            await self.close()
            return

        is_participant = await self._is_participant(room)
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        room = await self._get_room()
        if room is None:
            return

        is_participant = await self._is_participant(room)
        is_closed = await self._is_room_closed(room)

        if not is_participant or is_closed:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Chat room is closed or access is denied.'
            }))
            return

        data = json.loads(text_data)
        message = data.get('message', '').strip()
        if not message:
            return

        msg = await sync_to_async(Message.objects.create)(
            room_id=self.room_id,
            sender=self.user,
            text=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': msg.text,
                'sender': self.user.username,
            }
        )

        if getattr(self.user, 'role', '') == 'CUSTOMER':
            bot_msg = await self._create_bot_reply(message)
            if bot_msg is not None:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': bot_msg.text,
                        'sender': bot_msg.sender.username,
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def _get_room(self):
        return ChatRoom.objects.filter(id=self.room_id).first()

    @sync_to_async
    def _is_participant(self, room):
        return room.participants.filter(id=self.user.id).exists()

    @sync_to_async
    def _is_room_closed(self, room):
        return room.is_closed or Ticket.objects.filter(chat_room=room, status='closed').exists()

    @sync_to_async
    def _create_bot_reply(self, customer_message):
        room = ChatRoom.objects.filter(id=self.room_id).first()
        if room is None:
            return None
        ticket = Ticket.objects.filter(chat_room=room).first()
        return create_bot_reply(room=room, ticket=ticket, customer_message=customer_message)
