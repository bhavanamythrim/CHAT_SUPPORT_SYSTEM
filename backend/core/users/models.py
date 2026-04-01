from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    ROLE_CHOICES = (
        ("CUSTOMER", "Customer"),
        ("ADMIN", "Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CUSTOMER")
    phone = models.CharField(max_length=15, blank=True, null=True)
    govt_id = models.CharField(max_length=40, unique=True, blank=True, null=True)

    def __str__(self):
        return self.username


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference")
    sms = models.BooleanField(default=True)
    email_digest = models.BooleanField(default=True)
    in_app = models.BooleanField(default=False)
    escalation = models.BooleanField(default=True)

    def __str__(self):
        return f"NotificationPreference({self.user.username})"


class UserProfile(models.Model):
    THEME_CHOICES = (("light", "Light"), ("dark", "Dark"))
    FONT_SIZE_CHOICES = (("normal", "Normal"), ("large", "Large"), ("xlarge", "Extra Large"))
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

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    aadhaar_linked = models.BooleanField(default=False)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="light")
    font_size = models.CharField(max_length=10, choices=FONT_SIZE_CHOICES, default="normal")
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    mic_enabled = models.BooleanField(default=True)
    quick_chips_enabled = models.BooleanField(default=True)
    chat_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    notif_sms = models.BooleanField(default=True)
    notif_email = models.BooleanField(default=True)
    notif_inapp = models.BooleanField(default=False)
    notif_escalation = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
