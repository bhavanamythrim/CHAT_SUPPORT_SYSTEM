from django.contrib.auth import get_user_model
from django.db.models import Q

from tickets.models import Ticket

from .models import KnowledgeEntry, Message

BOT_USERNAME = "civic_assistant_bot"

INTENT_KEYWORDS = {
    "timings": ["timing", "time", "open", "close", "hours"],
    "bill_payment": ["bill", "payment", "paid", "receipt", "due"],
    "new_connection": ["new connection", "apply", "application", "connection"],
    "name_change": ["name change", "update name", "correction"],
    "outage_complaint": ["power cut", "outage", "no electricity", "water supply", "issue"],
    "documents": ["document", "proof", "id", "certificate"],
    "tracking": ["track", "status", "progress", "reference"],
}


def _get_or_create_bot_user():
    user_model = get_user_model()
    bot, created = user_model.objects.get_or_create(
        username=BOT_USERNAME,
        defaults={
            "email": "civic.assistant@local.help",
            "role": "CUSTOMER",
            "is_active": True,
        },
    )
    if created:
        bot.set_unusable_password()
        bot.save(update_fields=["password"])
    return bot


def _find_support_agent():
    user_model = get_user_model()
    return (
        user_model.objects.filter(is_active=True)
        .exclude(username=BOT_USERNAME)
        .filter(Q(role="ADMIN") | Q(is_staff=True) | Q(is_superuser=True))
        .order_by("id")
        .first()
    )


def _normalize(text):
    return (text or "").strip().lower()


def _detect_intent(user_text):
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in user_text for keyword in keywords):
            return intent
    return "general"


def _escalation_requested(user_text):
    escalation_tokens = [
        "agent",
        "human",
        "officer",
        "representative",
        "supervisor",
        "escalate",
        "connect",
        "talk to",
    ]
    return any(token in user_text for token in escalation_tokens)


def _knowledge_reply(department, intent, user_text):
    entries = KnowledgeEntry.objects.filter(is_active=True).filter(
        Q(department=department) | Q(department="general")
    )

    if intent != "general":
        intent_entries = entries.filter(intent__iexact=intent).order_by("priority", "id")
        for entry in intent_entries:
            return entry.answer

    entries = entries.order_by("priority", "id")
    for entry in entries:
        keywords = [k.strip().lower() for k in entry.trigger_keywords.split(",") if k.strip()]
        if keywords and any(keyword in user_text for keyword in keywords):
            return entry.answer

    return None


def _fallback_reply(department, intent):
    department_guides = {
        "post_office": "For Post Office help, share tracking/reference details. I can guide for parcel status, money order, and address update steps.",
        "water_board": "For Water Board help, share consumer number and area details. I can guide for new connection, leakage, and bill correction.",
        "electricity_board": "For Electricity Board help, share consumer number and latest bill details. I can guide for outage complaints, payment issues, and name change.",
        "municipality": "For Municipality services, share ward/zone and service type. I can guide on sanitation, certificates, and tax-related requests.",
        "general": "I can help with post office, water board, electricity board, and municipality requests. Tell me your issue and location to get exact steps.",
    }

    intent_suffix = {
        "timings": " Tell me your office/branch and I can provide timing guidance.",
        "bill_payment": " I can also guide payment and receipt steps.",
        "new_connection": " I can list connection application steps and required documents.",
        "name_change": " I can provide name correction process and document checklist.",
        "outage_complaint": " I can help you file outage/service interruption complaints quickly.",
        "documents": " I can provide the exact document checklist for your request.",
        "tracking": " Share ticket/reference details and I will guide tracking steps.",
        "general": "",
    }

    return department_guides.get(department, department_guides["general"]) + intent_suffix.get(intent, "")


def _escalate_to_human(ticket, room):
    assigned_agent = None
    if ticket is not None:
        assigned_agent = ticket.assigned_to
        if not assigned_agent or not (
            assigned_agent.is_staff
            or assigned_agent.is_superuser
            or getattr(assigned_agent, "role", "") == "ADMIN"
        ):
            assigned_agent = _find_support_agent()

        if assigned_agent:
            ticket.assigned_to = assigned_agent
            if ticket.status == "open":
                ticket.status = "in_progress"
            ticket.save(update_fields=["assigned_to", "status"])
            room.participants.add(assigned_agent)
            return f"I have connected your ticket to agent '{assigned_agent.username}'. They will continue shortly."

        if ticket.status == "open":
            ticket.status = "in_progress"
            ticket.save(update_fields=["status"])
        return "Your request has been escalated to human support. An available agent will respond soon."

    assigned_agent = _find_support_agent()
    if assigned_agent:
        room.participants.add(assigned_agent)
        return f"I have connected you to agent '{assigned_agent.username}'. They will join this chat shortly."

    return "I have escalated your chat to human support. An available agent will respond soon."


def create_bot_reply(room, ticket=None, customer_message=""):
    if room.is_closed or (ticket is not None and ticket.status == "closed"):
        return None

    user_text = _normalize(customer_message)
    intent = _detect_intent(user_text)

    department = "general"
    if ticket is not None and getattr(ticket, "department", None):
        department = ticket.department

    if _escalation_requested(user_text):
        reply = _escalate_to_human(ticket, room)
    else:
        reply = _knowledge_reply(department, intent, user_text)
        if not reply:
            reply = _fallback_reply(department, intent)

    bot_user = _get_or_create_bot_user()
    room.participants.add(bot_user)

    return Message.objects.create(
        room=room,
        sender=bot_user,
        text=reply,
    )
