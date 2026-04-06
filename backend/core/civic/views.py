import json
import math

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    ChatSession,
    Complaint,
    DocumentsRequired,
    KnowledgeBase,
    Message,
    Office,
    Service,
    ServiceUsageStat,
)
from .permissions import IsAdminUserOrReadOnly, IsOwnerOrStaff
from .serializers import (
    ChatSendSerializer,
    ChatSessionSerializer,
    ComplaintSerializer,
    DocumentsRequiredSerializer,
    KnowledgeBaseSerializer,
    MessageSerializer,
    OfficeSerializer,
    ServiceSerializer,
    ServiceUsageStatSerializer,
)
from .services import create_complaint_from_session, ensure_session_tracking_id, process_user_message
from notifications.models import CivicNotification
from users.models import NotificationPreference, UserProfile


@login_required
def landing_page(request):
    services = Service.objects.filter(is_active=True)
    session = ChatSession.objects.filter(user=request.user, status__in=["open", "escalated"]).order_by("-updated_at").first()
    if session is None:
        session = ChatSession.objects.create(user=request.user)
    ensure_session_tracking_id(session)
    chat_messages = session.messages.select_related("sender")
    nearby_offices = Office.objects.filter(service=session.service, is_active=True).order_by("city", "name")[:3] if session.service else []
    return render(
        request,
        "civic/landing.html",
        {
            "services": services,
            "session": session,
            "chat_messages": chat_messages,
            "nearby_offices": nearby_offices,
        },
    )


@login_required
def chat_page(request):
    return redirect("civic-landing")


@login_required
@require_POST
def end_chat_session(request):
    session_id = request.POST.get("session_id")
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return redirect("civic-landing")

    # Delete the session and its messages immediately (no history retention).
    session.delete()

    new_session = ChatSession.objects.create(user=request.user)
    ensure_session_tracking_id(new_session)
    return redirect("civic-landing")


@login_required
@require_POST
def send_chat_message(request):
    session_id = request.POST.get("session_id")
    content = (request.POST.get("content") or "").strip()

    if not session_id or not content:
        return JsonResponse({"error": "session_id and content are required"}, status=400)

    try:
        session = ChatSession.objects.select_related("user", "service", "assigned_agent").get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", "") == "ADMIN"):
        if session.user_id != request.user.id:
            return JsonResponse({"error": "Not allowed"}, status=403)

    try:
        user_msg, ai_msg, escalated = process_user_message(session, request.user, content)
    except Exception:
        return JsonResponse({"error": "Unable to process message right now. Please try again."}, status=500)
    return JsonResponse(
        {
            "session_id": session.id,
            "user_message": {
                "id": user_msg.id,
                "sender_role": user_msg.sender_role,
                "content": user_msg.content,
            },
            "ai_message": {
                "id": ai_msg.id,
                "sender_role": ai_msg.sender_role,
                "content": ai_msg.content,
            } if ai_msg else None,
            "escalated": escalated,
        }
    )


@login_required
def profile_page(request):
    # Backfill complaints for older escalated sessions that were created
    # before auto-complaint logic was added.
    missing_sessions = (
        ChatSession.objects
        .filter(user=request.user, status="escalated", complaint__isnull=True)
        .select_related("service", "assigned_agent")
    )
    for session in missing_sessions:
        latest_user_msg = (
            session.messages
            .filter(sender_role="citizen")
            .order_by("-created_at")
            .values_list("content", flat=True)
            .first()
        ) or "Auto-created complaint from escalated chat session."
        create_complaint_from_session(
            session=session,
            created_by=request.user,
            title=f"{session.service.name if session.service else 'Civic'} support escalation",
            description=latest_user_msg,
        )

    sessions = ChatSession.objects.filter(user=request.user).order_by("-updated_at")
    USER_FK = "created_by"
    all_complaints = Complaint.objects.filter(**{USER_FK: request.user}).order_by("-created_at")
    open_complaints = all_complaints.filter(status__in=["open", "in_progress", "escalated"])
    resolved_complaints = all_complaints.filter(status="resolved")
    closed_complaints = all_complaints.filter(status__in=["resolved", "closed"])

    total_complaints = all_complaints.count()
    open_count = open_complaints.count()
    resolved_count = resolved_complaints.count()
    reported_count = total_complaints

    issues_reported = reported_count
    issues_resolved = closed_complaints.count()
    session_count = sessions.count()
    complaint_count = total_complaints
    complaints = all_complaints

    escalated_session = (
        ChatSession.objects
        .filter(user=request.user, status="escalated")
        .order_by("-updated_at")
        .first()
    )

    recent_sessions = (
        sessions
        .annotate(message_count=Count("messages"))
        .select_related("service")[:4]
    )

    resolution_rate = int((resolved_count / total_complaints) * 100) if total_complaints else 0
    try:
        users_ahead = (
            Complaint.objects
            .values(USER_FK)
            .annotate(res=Count("id", filter=Q(status="resolved")))
            .filter(res__gt=resolved_count)
            .count()
        )
        city_rank = users_ahead + 1
    except Exception:
        city_rank = 100

    impact = {
        "reported": issues_reported,
        "resolved": issues_resolved,
        "rate": resolution_rate,
        "rank": city_rank,
    }

    completion_checks = {
        "name_contact": bool(request.user.username and (request.user.email or request.user.phone)),
        "address": bool(request.user.email),
        "aadhaar_linked": bool(request.user.govt_id),
        "phone": bool(request.user.phone),
        "id_proof": bool(request.user.govt_id),
    }
    profile_completion = int((sum(1 for v in completion_checks.values() if v) / len(completion_checks)) * 100)

    badges = [
        {"label": "First Report", "icon": "Star", "earned": issues_reported >= 1},
        {"label": "3 Issues", "icon": "Fire", "earned": issues_reported >= 3},
        {"label": "Quick Filer", "icon": "Bolt", "earned": session_count >= 5},
        {"label": "10 Resolved", "icon": "Trophy", "earned": issues_resolved >= 10},
        {"label": "Top Citizen", "icon": "Globe", "earned": issues_resolved >= 15},
    ]
    achievements = {
        "first_report": complaint_count >= 1,
        "three_issues": complaint_count >= 3,
        "quick_filer": session_count >= 1,
        "ten_resolved": issues_resolved >= 10,
        "top_citizen": issues_resolved >= 20,
    }

    saved_documents = [
        {"name": "Digital ID", "type": "Identity", "size": "120 KB", "uploaded": "Recent", "url": "#"},
        {"name": "Payment Receipts", "type": "Payments", "size": "390 KB", "uploaded": "Recent", "url": "#"},
        {"name": "Complaint Acknowledgements", "type": "Support", "size": "245 KB", "uploaded": "Recent", "url": "#"},
    ]

    escalation_events = []
    if escalated_session:
        escalation_events = [
            {"label": "Filed", "state": "done"},
            {"label": "Assigned", "state": "done"},
            {"label": "Review", "state": "active", "note": "Officer assigned. Expected update in 2 days."},
            {"label": "Work", "state": "pending"},
            {"label": "Closed", "state": "pending"},
        ]

    notification_prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
    notification_prefs_data = {
        "sms": notification_prefs.sms,
        "email_digest": notification_prefs.email_digest,
        "in_app": notification_prefs.in_app,
        "escalation": notification_prefs.escalation,
    }

    weekly_activity = (
        sessions
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(count=Count("id"))
        .order_by("week")
    )
    week_counts = [row["count"] for row in weekly_activity][-26:]
    if len(week_counts) < 26:
        week_counts = ([0] * (26 - len(week_counts))) + week_counts
    activity_json = json.dumps(week_counts)

    return render(
        request,
        "civic/profile.html",
        {
            "sessions": sessions[:10],
            "recent_sessions": recent_sessions,
            "complaints": complaints,
            "open_complaints": open_complaints,
            "total_complaints": total_complaints,
            "open_count": open_count,
            "resolved_count": resolved_count,
            "reported_count": reported_count,
            "resolution_rate": resolution_rate,
            "city_rank": city_rank,
            "total_sessions": session_count,
            "total_documents": len(saved_documents),
            "issues_reported": issues_reported,
            "issues_resolved": issues_resolved,
            "session_count": session_count,
            "complaint_count": complaint_count,
            "impact": impact,
            "profile_completion": profile_completion,
            "completion_checks": completion_checks,
            "badges": badges,
            "achievements": achievements,
            "saved_documents": saved_documents,
            "escalated_session": escalated_session,
            "escalation_events": escalation_events,
            "notification_prefs": notification_prefs_data,
            "activity_json": activity_json,
        },
    )


@login_required
def settings_page(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        allowed_langs = {"en", "ta", "hi", "te", "ml", "kn", "mr", "bn"}

        if action == "update_account":
            user.email = (request.POST.get("email") or "").strip()
            user.first_name = (request.POST.get("first_name") or "").strip()
            user.last_name = (request.POST.get("last_name") or "").strip()
            new_phone = (request.POST.get("phone") or "").strip()
            user.phone = new_phone
            user.save(update_fields=["email", "first_name", "last_name", "phone"])

            profile.phone = new_phone
            profile.save(update_fields=["phone", "updated_at"])
            messages.success(request, "Account details updated successfully.")
            return redirect("civic-settings")

        if action == "change_password":
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                updated_user = form.save()
                update_session_auth_hash(request, updated_user)
                messages.success(request, "Password changed successfully.")
            else:
                for field_errors in form.errors.values():
                    for error in field_errors:
                        messages.error(request, error)
            return redirect("civic-settings")

        if action == "update_appearance":
            theme = request.POST.get("theme", "light")
            font_size = request.POST.get("font_size", "normal")
            language = request.POST.get("language", "en")
            if theme in {"light", "dark"}:
                profile.theme = theme
            if font_size in {"normal", "large", "xlarge"}:
                profile.font_size = font_size
            if language in allowed_langs:
                profile.language = language
            profile.save(update_fields=["theme", "font_size", "language", "updated_at"])
            messages.success(request, "Appearance settings saved.")
            return redirect("civic-settings")

        if action == "update_chat":
            chat_language = request.POST.get("chat_language", "en")
            if chat_language in allowed_langs:
                profile.chat_language = chat_language
            profile.mic_enabled = "mic_enabled" in request.POST
            profile.quick_chips_enabled = "quick_chips_enabled" in request.POST
            profile.save(update_fields=["chat_language", "mic_enabled", "quick_chips_enabled", "updated_at"])
            messages.success(request, "Chat preferences saved.")
            return redirect("civic-settings")

    return render(
        request,
        "civic/settings.html",
        {
            "user": user,
            "profile": profile,
            "active_page": "settings",
        },
    )


@require_POST
@login_required
def settings_toggle(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    field = data.get("field")
    value = data.get("value")
    if isinstance(value, str):
        value = value.lower() in {"1", "true", "yes", "on"}

    allowed_fields = {
        "notif_sms",
        "notif_email",
        "notif_inapp",
        "notif_escalation",
        "mic_enabled",
        "quick_chips_enabled",
        "theme",
        "font_size",
        "chat_language",
        "language",
    }
    if field not in allowed_fields:
        return JsonResponse({"error": "Field not allowed"}, status=400)

    if field == "theme" and value not in {"light", "dark"}:
        return JsonResponse({"error": "Invalid theme"}, status=400)
    if field == "font_size" and value not in {"normal", "large", "xlarge"}:
        return JsonResponse({"error": "Invalid font_size"}, status=400)
    if field in {"chat_language", "language"} and value not in {"en", "ta", "hi", "te", "ml", "kn", "mr", "bn"}:
        return JsonResponse({"error": "Invalid language"}, status=400)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    setattr(profile, field, value)
    profile.save(update_fields=[field, "updated_at"])
    return JsonResponse({"status": "ok", "field": field, "value": value})


@require_POST
@login_required
def export_data(request):
    user = request.user
    sessions = list(
        ChatSession.objects.filter(user=user).values(
            "id",
            "service_id",
            "status",
            "created_at",
            "updated_at",
        )
    )
    complaints = list(
        Complaint.objects.filter(created_by=user).values(
            "tracking_id",
            "title",
            "status",
            "created_at",
            "updated_at",
        )
    )
    export_payload = {
        "username": user.username,
        "email": user.email,
        "joined": user.date_joined.isoformat(),
        "sessions": sessions,
        "complaints": complaints,
    }

    response = HttpResponse(
        json.dumps(export_payload, indent=2, default=str),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{user.username}_civic_data.json"'
    return response


@require_POST
@login_required
def delete_account(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    password = data.get("password", "")
    if not request.user.check_password(password):
        return JsonResponse({"error": "Incorrect password"}, status=400)

    user = request.user
    from django.contrib.auth import logout

    logout(request)
    user.delete()
    return JsonResponse({"status": "ok", "redirect": "/login/"})


@user_passes_test(lambda u: u.is_staff or u.is_superuser or getattr(u, "role", "") == "ADMIN")
def admin_dashboard_page(request):
    data = {
        "total_users": ChatSession.objects.values("user_id").distinct().count(),
        "total_sessions": ChatSession.objects.count(),
        "open_complaints": Complaint.objects.filter(status__in=["open", "in_progress"]).count(),
        "today_queries": Message.objects.filter(created_at__date=timezone.now().date(), sender_role="citizen").count(),
        "services_count": Service.objects.count(),
        "knowledge_count": KnowledgeBase.objects.count(),
        "offices_count": Office.objects.count(),
        "documents_count": DocumentsRequired.objects.count(),
        "service_usage": Service.objects.annotate(total=Count("usage_stats")).order_by("name"),
        "usage_stats": ServiceUsageStat.objects.select_related("service").order_by("-date")[:20],
    }
    return render(request, "civic/admin_dashboard.html", data)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by("name")
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]


class OfficeViewSet(viewsets.ModelViewSet):
    queryset = Office.objects.select_related("service").all().order_by("name")
    serializer_class = OfficeSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeBase.objects.select_related("service").all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]


class DocumentsRequiredViewSet(viewsets.ModelViewSet):
    queryset = DocumentsRequired.objects.select_related("service").all()
    serializer_class = DocumentsRequiredSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]


class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = ChatSession.objects.select_related("user", "service", "assigned_agent")
        if self.request.user.is_staff or self.request.user.is_superuser or getattr(self.request.user, "role", "") == "ADMIN":
            return qs
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        session = serializer.save(user=self.request.user)
        ensure_session_tracking_id(session)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        session = self.get_object()
        session.status = "escalated"
        session.save(update_fields=["status", "updated_at"])
        return Response({"status": "escalated"})


class MessageViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = Message.objects.select_related("session", "sender")
        if self.request.user.is_staff or self.request.user.is_superuser or getattr(self.request.user, "role", "") == "ADMIN":
            return qs
        return qs.filter(session__user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return ChatSendSerializer
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.validated_data["session"]

        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", "") == "ADMIN"):
            if session.user_id != request.user.id:
                return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        user_msg, ai_msg, escalated = process_user_message(session, request.user, serializer.validated_data["content"])
        return Response(
            {
                "session_id": session.id,
                "user_message_id": user_msg.id,
                "ai_message_id": ai_msg.id if ai_msg else None,
                "user_message": user_msg.content,
                "ai_message": ai_msg.content if ai_msg else None,
                "escalated": escalated,
            },
            status=status.HTTP_201_CREATED,
        )


class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = Complaint.objects.select_related("session", "service", "created_by", "assigned_to")
        if self.request.user.is_staff or self.request.user.is_superuser or getattr(self.request.user, "role", "") == "ADMIN":
            return qs
        return qs.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        session = serializer.validated_data["session"]
        lat_raw = self.request.data.get("complaint_lat") or self.request.data.get("latitude")
        lng_raw = self.request.data.get("complaint_lng") or self.request.data.get("longitude")
        location_address = (self.request.data.get("complaint_address") or self.request.data.get("location_address") or "").strip()

        latitude = None
        longitude = None
        try:
            if lat_raw not in (None, ""):
                latitude = float(lat_raw)
            if lng_raw not in (None, ""):
                longitude = float(lng_raw)
        except (TypeError, ValueError):
            latitude = None
            longitude = None

        complaint = create_complaint_from_session(
            session=session,
            created_by=self.request.user,
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
        )
        serializer.instance = complaint


class ServiceUsageStatViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = ServiceUsageStat.objects.select_related("service").all()
    serializer_class = ServiceUsageStatSerializer
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]


def _distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


class SessionSummaryApiView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get("session_id")
        if not session_id:
            return JsonResponse({"error": "session_id is required"}, status=400)

        session = ChatSession.objects.filter(id=session_id, user=request.user).first()
        if session is None:
            return JsonResponse({"error": "Session not found"}, status=404)

        recent = list(session.messages.order_by("-created_at").values_list("content", flat=True)[:8])
        text = " ".join(reversed(recent)).lower()

        topic = session.service.name if session.service else "General civic support"
        department = session.service.name if session.service else "General"
        urgency = "High" if any(token in text for token in ["urgent", "emergency", "immediately"]) else "Normal"
        query_type = "Complaint" if any(token in text for token in ["complaint", "issue", "report"]) else "Information"

        return JsonResponse(
            {
                "topic": topic,
                "department": department,
                "urgency": urgency,
                "query_type": query_type,
            }
        )


class NearbyOfficeApiView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        lat_raw = request.GET.get("lat")
        lng_raw = request.GET.get("lng")
        service_id = request.GET.get("service_id")
        limit_raw = request.GET.get("limit", "5")

        try:
            lat = float(lat_raw) if lat_raw is not None else None
            lng = float(lng_raw) if lng_raw is not None else None
            limit = max(1, min(int(limit_raw), 10))
        except ValueError:
            return JsonResponse({"error": "Invalid coordinates"}, status=400)

        if lat is None or lng is None:
            return JsonResponse({"error": "lat and lng query params required"}, status=400)

        qs = Office.objects.filter(is_active=True).select_related("service")
        try:
            service_id_int = int(service_id) if service_id not in (None, "") else 0
        except (TypeError, ValueError):
            service_id_int = 0
        if service_id_int > 0:
            qs = qs.filter(service_id=service_id_int)
        qs = qs.filter(latitude__isnull=False, longitude__isnull=False)

        rows = []
        for office in qs:
            distance = None
            if office.latitude is not None and office.longitude is not None:
                distance = _distance_km(lat, lng, float(office.latitude), float(office.longitude))
                rows.append((distance, office))

        rows.sort(key=lambda row: (row[0] is None, row[0] if row[0] is not None else 999999))
        payload = []
        for distance, office in rows[:limit]:
            rounded = round(distance, 1) if distance is not None else None
            distance_label = None
            if rounded is not None:
                distance_label = f"{rounded} km" if rounded >= 1 else f"{int(max(distance, 0) * 1000)} m"
            payload.append(
                {
                    "id": office.id,
                    "name": office.name,
                    "address": office.address,
                    "city": office.city,
                    "timings": office.timings or "Mon-Sat 10AM-5PM",
                    "opening_hours": office.timings or "Mon-Sat 10AM-5PM",
                    "service": office.service.name,
                    "distance_km": rounded,
                    "distance_label": distance_label,
                    "is_open": bool(office.timings),
                    "status": "Open" if office.timings else "Unknown",
                    "office_type": office.service.name,
                    "map_link": office.google_map_link or f"https://www.google.com/maps/search/?api=1&query={office.latitude},{office.longitude}",
                    "maps_url": office.google_map_link or f"https://www.google.com/maps/search/?api=1&query={office.latitude},{office.longitude}",
                }
            )

        return JsonResponse({"results": payload})


@require_POST
@login_required
def agent_takeover(request, session_id):
    try:
        session = ChatSession.objects.select_related("user", "assigned_agent").get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    is_agent = request.user.is_staff or request.user.groups.filter(name="agents").exists() or getattr(request.user, "role", "") == "ADMIN"
    if not is_agent:
        return JsonResponse({"error": "Not authorized"}, status=403)

    session.agent_active = True
    session.assigned_agent = request.user
    session.agent_joined_at = timezone.now()
    session.status = "escalated"
    session.save(update_fields=["agent_active", "assigned_agent", "agent_joined_at", "status", "updated_at"])

    join_message = f"Agent {request.user.get_full_name() or request.user.username} has joined the session. The AI assistant is now paused."
    msg = Message.objects.create(
        session=session,
        sender=request.user,
        content=join_message,
        sender_role="agent",
        is_from_ai=False,
        language=session.language_preference,
    )

    channel_layer = get_channel_layer()
    room_group_name = f"civic_session_{session_id}"
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            "type": "chat.event",
            "payload": {
                "session_id": session.id,
                "message": join_message,
                "sender_role": "agent",
                "sender": request.user.username,
                "sender_username": request.user.username,
                "is_from_ai": False,
                "system": True,
                "message_id": msg.id,
            },
        },
    )

    return JsonResponse(
        {
            "status": "ok",
            "message": "Takeover successful. AI is now silent.",
            "session_id": session_id,
            "agent": request.user.username,
        }
    )


@require_POST
@login_required
def agent_end_takeover(request, session_id):
    try:
        session = ChatSession.objects.select_related("user", "assigned_agent").get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    is_agent = request.user.is_staff or request.user.groups.filter(name="agents").exists() or getattr(request.user, "role", "") == "ADMIN"
    if not is_agent:
        return JsonResponse({"error": "Not authorized"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}
    action = payload.get("action", "end")

    session.agent_active = False
    session.agent_ended_at = timezone.now()
    if action == "resolve":
        session.status = "closed"
    else:
        session.status = "open"
    session.save(update_fields=["agent_active", "agent_ended_at", "status", "updated_at"])

    if action == "resolve":
        end_message = "Your session has been resolved by the agent. Thank you for using Smart Civic HelpDesk."
    else:
        end_message = "Agent has left the session. The AI assistant will now continue to help you."

    msg = Message.objects.create(
        session=session,
        sender=request.user,
        content=end_message,
        sender_role="agent",
        is_from_ai=False,
        language=session.language_preference,
    )

    channel_layer = get_channel_layer()
    room_group_name = f"civic_session_{session_id}"
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            "type": "chat.event",
            "payload": {
                "session_id": session.id,
                "message": end_message,
                "sender_role": "agent",
                "sender": request.user.username,
                "sender_username": request.user.username,
                "is_from_ai": False,
                "system": True,
                "message_id": msg.id,
            },
        },
    )

    return JsonResponse(
        {
            "status": "ok",
            "message": f"Takeover ended. Action: {action}",
            "session_id": session_id,
        }
    )


@login_required
def agent_dashboard(request):
    is_agent = request.user.is_staff or request.user.groups.filter(name="agents").exists() or getattr(request.user, "role", "") == "ADMIN"
    if not is_agent:
        return redirect("civic-chat")

    my_sessions = (
        ChatSession.objects.select_related("user", "service")
        .filter(assigned_agent=request.user)
        .order_by("-created_at")
    )
    return render(
        request,
        "civic/agent_dashboard.html",
        {
            "my_sessions": my_sessions,
            "active_page": "agent",
        },
    )

