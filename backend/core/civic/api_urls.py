from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    agent_end_takeover,
    agent_takeover,
    ChatSessionViewSet,
    ComplaintViewSet,
    DocumentsRequiredViewSet,
    KnowledgeBaseViewSet,
    MessageViewSet,
    NearbyOfficeApiView,
    OfficeViewSet,
    SessionSummaryApiView,
    ServiceUsageStatViewSet,
    ServiceViewSet,
)

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="civic-service")
router.register("offices", OfficeViewSet, basename="civic-office")
router.register("knowledge", KnowledgeBaseViewSet, basename="civic-knowledge")
router.register("documents", DocumentsRequiredViewSet, basename="civic-documents")
router.register("sessions", ChatSessionViewSet, basename="civic-session")
router.register("messages", MessageViewSet, basename="civic-message")
router.register("complaints", ComplaintViewSet, basename="civic-complaint")
router.register("analytics", ServiceUsageStatViewSet, basename="civic-analytics")

urlpatterns = router.urls + [
    path("session/summary/", SessionSummaryApiView.as_view(), name="civic-session-summary"),
    path("offices/nearby/", NearbyOfficeApiView.as_view(), name="civic-offices-nearby"),
    path("sessions/<int:session_id>/takeover/", agent_takeover, name="agent-takeover"),
    path("sessions/<int:session_id>/end-takeover/", agent_end_takeover, name="agent-end-takeover"),
]
