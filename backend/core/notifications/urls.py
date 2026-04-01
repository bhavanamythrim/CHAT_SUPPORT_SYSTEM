from django.urls import path

from .views import mark_all_notifications_read, mark_notification_read

urlpatterns = [
    path("read/<int:notification_id>/", mark_notification_read, name="notification-read"),
    path("read-all/", mark_all_notifications_read, name="notification-read-all"),
]
