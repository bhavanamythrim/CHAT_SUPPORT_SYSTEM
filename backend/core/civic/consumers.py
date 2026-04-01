import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .ai_responder import generate_response
from .models import ChatSession, Message
from .services import needs_escalation, process_user_message


class CivicChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.session_id = int(self.scope["url_route"]["kwargs"]["session_id"])
        self.group_name = f"civic_session_{self.session_id}"

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        allowed = await self._has_access()
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
            content = (payload.get("message") or "").strip()
            if not content:
                return

            result = await self._process(content)
            await self.channel_layer.group_send(self.group_name, {"type": "chat.event", "payload": result})
        except Exception:
            await self.send(text_data=json.dumps({"error": "Unable to process message"}))

    async def chat_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    @sync_to_async
    def _has_access(self):
        session = ChatSession.objects.filter(id=self.session_id).select_related("user").first()
        if not session:
            return False
        if self.user.is_staff or self.user.is_superuser or getattr(self.user, "role", "") == "ADMIN":
            return True
        return session.user_id == self.user.id

    @sync_to_async
    def _process(self, content):
        session = ChatSession.objects.select_related("user", "service", "assigned_agent").get(id=self.session_id)
        user_role = getattr(self.user, "role", "") or ""
        is_support = self.user.is_staff or self.user.is_superuser or user_role == "ADMIN"

        # Human agent takeover: AI remains silent for citizen messages.
        if session.agent_active:
            if is_support:
                sender_role = "admin" if user_role == "ADMIN" else "agent"
                msg = Message.objects.create(
                    session=session,
                    sender=self.user,
                    sender_role=sender_role,
                    content=content,
                    language=session.language_preference,
                    is_from_ai=False,
                )
                session.last_message_at = msg.created_at
                session.save(update_fields=["last_message_at", "updated_at"])
                return {
                    "session_id": session.id,
                    "message": msg.content,
                    "sender_role": sender_role,
                    "sender": self.user.username,
                    "sender_username": self.user.username,
                    "is_from_ai": False,
                    "system": False,
                    "agent_active": True,
                }

            msg = Message.objects.create(
                session=session,
                sender=self.user,
                sender_role="citizen",
                content=content,
                language=session.language_preference,
                is_from_ai=False,
            )
            session.last_message_at = msg.created_at
            session.save(update_fields=["last_message_at", "updated_at"])
            return {
                "session_id": session.id,
                "user_message": {
                    "id": msg.id,
                    "sender_role": msg.sender_role,
                    "sender_username": self.user.username,
                    "content": msg.content,
                    "language": msg.language,
                    "created_at": msg.created_at.isoformat(),
                },
                "ai_message": None,
                "escalated": session.status == "escalated",
                "agent_active": True,
            }

        history_rows = list(
            Message.objects.filter(session=session)
            .order_by("-created_at")
            .values("sender_role", "content")[:6]
        )

        user_msg, ai_msg, escalated = process_user_message(session, self.user, content)

        # Keep existing complaint/escalation flow, but improve normal AI response quality
        # using fuzzy KB + LLM synthesis.
        if (
            not is_support
            and ai_msg is not None
            and not escalated
            and not needs_escalation(content)
        ):
            history = []
            for row in reversed(history_rows):
                role = "assistant" if row["sender_role"] == "assistant" else "user"
                history.append({"role": role, "content": row["content"]})

            result = generate_response(
                user_message=content,
                session_history=history,
                user_language=user_msg.language,
            )
            ai_msg.content = result["response"]
            ai_msg.language = result["language"]
            ai_msg.save(update_fields=["content", "language"])

        return {
            "session_id": session.id,
            "user_message": {
                "id": user_msg.id,
                "sender_role": user_msg.sender_role,
                "sender_username": self.user.username,
                "content": user_msg.content,
                "language": user_msg.language,
                "created_at": user_msg.created_at.isoformat(),
            },
            "ai_message": {
                "id": ai_msg.id,
                "sender_role": ai_msg.sender_role,
                "content": ai_msg.content,
                "language": ai_msg.language,
                "created_at": ai_msg.created_at.isoformat(),
            }
            if ai_msg
            else None,
            "escalated": escalated,
        }
