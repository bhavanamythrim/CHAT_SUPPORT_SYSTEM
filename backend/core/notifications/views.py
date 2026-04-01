from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from .models import CivicNotification


@login_required
def mark_notification_read(request, notification_id):
    item = get_object_or_404(CivicNotification, id=notification_id, user=request.user)
    item.is_read = True
    item.save(update_fields=["is_read"])
    if item.link:
        return redirect(item.link)
    return redirect("civic-landing")


@login_required
def mark_all_notifications_read(request):
    CivicNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("civic-landing")
