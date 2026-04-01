from django.db import models
from django.conf import settings
from chat.models import ChatRoom

User = settings.AUTH_USER_MODEL


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    DEPARTMENT_CHOICES = [
        ('post_office', 'Post Office'),
        ('water_board', 'Water Board'),
        ('electricity_board', 'Electricity Board'),
        ('municipality', 'Municipality'),
        ('general', 'General Help Desk'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.CharField(max_length=40, choices=DEPARTMENT_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )

    chat_room = models.OneToOneField(
        ChatRoom,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.chat_room:
            room = ChatRoom.objects.create(is_closed=self.status == 'closed')
            room.participants.add(self.created_by)
            self.chat_room = room
            super().save(update_fields=['chat_room'])

        if self.assigned_to and self.chat_room:
            self.chat_room.participants.add(self.assigned_to)

        if self.chat_room:
            should_close = self.status == 'closed'
            if self.chat_room.is_closed != should_close:
                self.chat_room.is_closed = should_close
                self.chat_room.save(update_fields=['is_closed'])

    def __str__(self):
        return f"{self.title} ({self.status})"
