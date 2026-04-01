from .models import CivicNotification
from civic.models import ChatSession, Message
from civic.models import Complaint


def civic_notifications(request):
    if not request.user.is_authenticated:
        return {"notif_count": 0, "notif_items": [], "sidebar_sessions": []}

    qs = CivicNotification.objects.filter(user=request.user).order_by("-created_at")
    sessions = (
        ChatSession.objects.filter(user=request.user)
        .order_by("-updated_at")
        .only("id", "status", "updated_at", "service_id", "complaint_tracking_id")[:5]
    )

    sidebar_sessions = []
    for session in sessions:
        first_msg = (
            Message.objects.filter(session=session, sender_role="citizen")
            .order_by("created_at")
            .values_list("content", flat=True)
            .first()
        )
        service_name = session.service.name if session.service else "Civic Query"
        title = (first_msg or f"{service_name} assistance").strip()
        sidebar_sessions.append(
            {
                "id": session.id,
                "title": title[:42],
                "status": session.status,
                "updated_at": session.updated_at,
            }
        )

    return {
        "notif_count": qs.filter(is_read=False).count(),
        "unread_notification_count": qs.filter(is_read=False).count(),
        "open_complaint_count": Complaint.objects.filter(
            created_by=request.user,
            status__in=["open", "in_progress"],
        ).count(),
        "notif_items": qs[:5],
        "sidebar_sessions": sidebar_sessions,
    }
