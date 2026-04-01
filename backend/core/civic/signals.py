from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ChatLog, Message


@receiver(post_save, sender=Message)
def record_chat_log(sender, instance, created, **kwargs):
    if not created:
        return
    ChatLog.objects.create(
        session=instance.session,
        message=instance,
        event_type="message_created",
        payload={
            "sender_role": instance.sender_role,
            "language": instance.language,
            "is_from_ai": instance.is_from_ai,
        },
    )
