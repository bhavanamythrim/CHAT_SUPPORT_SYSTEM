from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class ChatRoom(models.Model):
    participants = models.ManyToManyField(
        User,
        related_name="chat_rooms"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"Room {self.id}"


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    text = models.TextField()
    file = models.FileField(
        upload_to='chat_files/',
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender}"


class KnowledgeEntry(models.Model):
    DEPARTMENT_CHOICES = [
        ('post_office', 'Post Office'),
        ('water_board', 'Water Board'),
        ('electricity_board', 'Electricity Board'),
        ('municipality', 'Municipality'),
        ('general', 'General Help Desk'),
    ]

    department = models.CharField(max_length=40, choices=DEPARTMENT_CHOICES, default='general')
    intent = models.CharField(max_length=60, blank=True, default='')
    trigger_keywords = models.CharField(
        max_length=300,
        help_text='Comma-separated keywords used to match user messages.',
        blank=True,
        default='',
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "id")

    def __str__(self):
        return f"{self.get_department_display()} - {self.question}"
