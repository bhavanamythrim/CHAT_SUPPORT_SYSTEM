from django.conf import settings
from django.db import models
from django.utils import timezone


class Service(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Office(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="offices")
    name = models.CharField(max_length=160)
    address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, default="Tamil Nadu")
    pincode = models.CharField(max_length=12, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    timings = models.CharField(max_length=200, blank=True)
    google_map_link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.city})"


class KnowledgeBase(models.Model):
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("ta", "Tamil"),
        ("hi", "Hindi"),
        ("te", "Telugu"),
        ("ml", "Malayalam"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
    )

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="knowledge_entries", null=True, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    question = models.CharField(max_length=255)
    answer = models.TextField()
    keywords = models.CharField(max_length=300, help_text="Comma-separated keywords")
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("priority", "id")


class DocumentsRequired(models.Model):
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("ta", "Tamil"),
        ("hi", "Hindi"),
        ("te", "Telugu"),
        ("ml", "Malayalam"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
    )

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=180)
    details = models.TextField(help_text="Use bullet style text for required documents")
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    is_active = models.BooleanField(default=True)


class ChatSession(models.Model):
    STATUS_CHOICES = (("open", "Open"), ("escalated", "Escalated"), ("closed", "Closed"))
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("ta", "Tamil"),
        ("hi", "Hindi"),
        ("te", "Telugu"),
        ("ml", "Malayalam"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="civic_sessions")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_sessions")
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_civic_sessions")
    agent_active = models.BooleanField(
        default=False,
        help_text="True when a human agent has taken over. AI will not respond.",
    )
    agent_joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when agent took over",
    )
    agent_ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when agent ended takeover",
    )
    language_preference = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="open")
    complaint_tracking_id = models.CharField(max_length=30, unique=True, blank=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    ROLE_CHOICES = (("citizen", "Citizen"), ("agent", "Agent"), ("admin", "Admin"), ("assistant", "Assistant"))
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("ta", "Tamil"),
        ("hi", "Hindi"),
        ("te", "Telugu"),
        ("ml", "Malayalam"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    sender_role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField()
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="en")
    is_from_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class Complaint(models.Model):
    STATUS_CHOICES = (("open", "Open"), ("in_progress", "In Progress"), ("resolved", "Resolved"), ("closed", "Closed"))

    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name="complaint")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_complaints")
    title = models.CharField(max_length=200)
    description = models.TextField()
    tracking_id = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatLog(models.Model):
    EVENT_CHOICES = (("message_created", "Message Created"), ("session_updated", "Session Updated"))

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="logs")
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ServiceUsageStat(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="usage_stats")
    date = models.DateField()
    total_queries = models.PositiveIntegerField(default=0)
    escalated_queries = models.PositiveIntegerField(default=0)
    complaints_raised = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("service", "date")
        ordering = ("-date", "service_id")
