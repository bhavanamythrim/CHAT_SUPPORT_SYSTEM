from datetime import date
import math
import re
from urllib.parse import quote_plus

from django.contrib.auth import get_user_model
from django.db.models import Q

from notifications.models import CivicNotification
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


LANG_PATTERNS = {
    "ta": re.compile(r"[\u0B80-\u0BFF]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
    "te": re.compile(r"[\u0C00-\u0C7F]"),
    "ml": re.compile(r"[\u0D00-\u0D7F]"),
    "kn": re.compile(r"[\u0C80-\u0CFF]"),
    "bn": re.compile(r"[\u0980-\u09FF]"),
    "mr": re.compile(r"[\u0900-\u097F]"),
}
NON_WORD_PATTERN = re.compile(r"[^a-z0-9\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\s]+")
LOCATION_SPLIT_PATTERN = re.compile(r"\bin\s+([a-z0-9,\-\s]+)$", re.IGNORECASE)
LAT_LON_PATTERN = re.compile(r"(?:lat(?:itude)?\s*)?(-?\d+(?:\.\d+)?)\s*,\s*(?:lon(?:gitude)?\s*)?(-?\d+(?:\.\d+)?)", re.IGNORECASE)
SERVICE_HINTS = {
    "post": ["post", "postal", "parcel", "speed post", "registered post"],
    "electricity": ["electricity", "eb", "tneb", "current bill", "power", "meter", "connection"],
    "bank": ["bank", "kyc", "loan", "atm", "account", "passbook"],
    "government": ["ration", "certificate", "pension", "community", "land record", "govt", "government"],
}
INTENT_HINTS = {
    "timings": ["timing", "time", "open", "close", "working hours"],
    "documents": ["document", "documents", "proof", "id proof", "required docs", "checklist"],
    "office": ["office", "near", "nearest", "address", "location", "map", "contact"],
    "tracking": ["track", "tracking", "status", "reference", "complaint id", "ticket"],
    "payment": ["bill", "payment", "pay", "receipt", "due"],
    "new_connection": ["new connection", "apply", "application", "connection"],
}
GREETING_TOKENS = {
    "hi",
    "hello",
    "hey",
    "help",
    "i want help",
    "need help",
    "assist me",
    "namaste",
    "namaskar",
    "namaskaram",
    "नमस्ते",
    "नमस्कार",
    "నమస్కారం",
    "നമസ്കാരം",
    "ನಮಸ್ಕಾರ",
    "নমস্কার",
}
THANKS_TOKENS = {
    "thanks",
    "thank you",
    "thanks a lot",
    "thankyou",
    "thank u",
    "thx",
    "धन्यवाद",
    "शुक्रिया",
    "ధన్యవాదాలు",
    "നന്ദി",
    "ಧನ್ಯವಾದ",
    "ধন্যবাদ",
}
DEFAULT_QA_ENTRIES = [
    {
        "service_keys": ["post", "postal", "post-office"],
        "keywords": ["timing", "time", "working hours", "open", "close"],
        "answer_en": "Post Office counters usually work Monday to Saturday, 10:00 AM to 5:00 PM. Timings can vary by branch.",
    },
    {
        "service_keys": ["electricity", "eb", "tneb", "electricity-board"],
        "keywords": ["bill", "payment", "pay", "due"],
        "answer_en": "For EB bill payment, keep your service number ready and pay via official portal/app, e-Sevai center, or section office.",
    },
    {
        "service_keys": ["electricity", "eb", "tneb", "electricity-board"],
        "keywords": ["name change", "change name", "correction"],
        "answer_en": "EB name change usually needs latest bill, ID proof, address proof, and ownership or rental proof.",
    },
    {
        "service_keys": ["bank", "bank-services"],
        "keywords": ["kyc", "update", "account"],
        "answer_en": "For bank KYC update, visit branch with ID and address proof, fill KYC form, and submit self-attested copies.",
    },
    {
        "service_keys": ["government", "govt", "government-offices"],
        "keywords": ["ration", "ration card", "apply"],
        "answer_en": "Ration card application can be submitted via e-Sevai with family details, Aadhaar, and address proof.",
    },
    {
        "service_keys": ["government", "govt", "government-offices"],
        "keywords": ["birth certificate", "community certificate", "certificate"],
        "answer_en": "Certificates can be applied through e-Sevai or Taluk/Municipal office using required identity and supporting documents.",
    },
    {
        "service_keys": ["government", "govt", "government-offices", "passport"],
        "keywords": ["passport", "apply passport", "passport renewal"],
        "answer_en": "Passport applications can be started online via Passport Seva. Keep ID proof, address proof, and date-of-birth document ready.",
    },
    {
        "service_keys": ["government", "govt", "government-offices", "visa"],
        "keywords": ["visa", "visa apply", "visa appointment"],
        "answer_en": "Visa process depends on destination country. Start with the embassy or visa portal, then prepare passport, photos, financial proof, and travel purpose documents.",
    },
    {
        "service_keys": ["government", "govt", "government-offices", "license", "driving"],
        "keywords": ["license", "driving license", "dl", "llr"],
        "answer_en": "Driving license can be applied through Parivahan portal or RTO. Usually you begin with learner license, then driving test for permanent license.",
    },
]


def detect_language(text, fallback="en"):
    if not text:
        return fallback
    for code, pattern in LANG_PATTERNS.items():
        if pattern.search(text):
            return code
    return fallback


def generate_tracking_id(prefix="CMP"):
    return f"{prefix}-{date.today().strftime('%Y%m%d')}"


def _normalize_text(text):
    lowered = (text or "").lower().strip()
    cleaned = NON_WORD_PATTERN.sub(" ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _next_tracking_id(model, field_name, prefix):
    base = generate_tracking_id(prefix)
    n = 1
    value = f"{base}-{n:04d}"
    while model.objects.filter(**{field_name: value}).exists():
        n += 1
        value = f"{base}-{n:04d}"
    return value


def ensure_session_tracking_id(session):
    if not session.complaint_tracking_id:
        session.complaint_tracking_id = _next_tracking_id(ChatSession, "complaint_tracking_id", "SES")
        session.save(update_fields=["complaint_tracking_id"])


def _keyword_score(entry_keywords, text):
    query = _normalize_text(text)
    keywords = [k.strip().lower() for k in (entry_keywords or "").split(",") if k.strip()]
    if not keywords:
        return 0

    score = 0
    for keyword in keywords:
        if keyword in query:
            score += 2 if " " in keyword else 1
    return score


def get_session_history(session, limit=6):
    if not session:
        return []

    try:
        recent_messages = Message.objects.filter(session=session).order_by("-created_at")[:limit]
        history = []
        for msg in reversed(list(recent_messages)):
            content = getattr(msg, "content", "") or ""
            sender_role = getattr(msg, "sender_role", "Citizen")
            if content:
                history.append({"role": sender_role, "content": content})
        return history
    except Exception:
        return []


def build_search_query(current_message, history):
    vague_words = [
        "it",
        "that",
        "this",
        "them",
        "for it",
        "for that",
        "the same",
        "above",
        "mentioned",
        "those",
        "these",
        "அது",
        "இது",
        "அவை",
    ]

    message_lower = (current_message or "").lower().strip()
    is_vague = len(message_lower.split()) <= 6 or any(w in message_lower for w in vague_words)
    if not is_vague or not history:
        return current_message

    recent_citizen_msgs = [h["content"] for h in history[-4:] if h["role"] == "citizen"][-2:]
    if not recent_citizen_msgs:
        return current_message

    stop_words = {
        "how",
        "do",
        "i",
        "can",
        "what",
        "is",
        "the",
        "a",
        "an",
        "to",
        "for",
        "in",
        "of",
        "and",
        "or",
        "me",
        "my",
        "get",
        "apply",
        "need",
        "want",
        "please",
    }
    combined = current_message
    for prev_msg in recent_citizen_msgs:
        keywords = [w for w in prev_msg.lower().split() if w not in stop_words and len(w) > 2]
        combined = combined + " " + " ".join(keywords[:5])
    return combined.strip()


def _builtin_qa_answer(service, text, language):
    if language != "en":
        return None

    normalized = _normalize_text(text)
    service_text = ""
    if service:
        service_text = f"{(service.code or '').lower()} {(service.name or '').lower()}"

    for entry in DEFAULT_QA_ENTRIES:
        if service_text:
            has_service_match = any(token in service_text for token in entry["service_keys"])
        else:
            has_service_match = any(token in normalized for token in entry["service_keys"])
        if not has_service_match:
            continue
        if any(keyword in normalized for keyword in entry["keywords"]):
            return entry["answer_en"]
    return None


def _detect_intent(text):
    normalized = _normalize_text(text)
    for intent, keywords in INTENT_HINTS.items():
        for keyword in keywords:
            if keyword in normalized:
                return intent
    return "general"


def _is_greeting_or_help(text):
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if normalized in GREETING_TOKENS:
        return True
    return normalized.startswith("hi ") or normalized.startswith("hello ") or normalized.startswith("hey ")


def _is_thanks(text):
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if normalized in THANKS_TOKENS:
        return True
    return normalized.startswith("thanks ") or normalized.startswith("thank you ")


def _greeting_reply(language):
    if language == "ta":
        return "வணக்கம்! உங்களுக்கு என்ன உதவி வேண்டும்? சேவை பெயரும் இடமும் சொல்லுங்கள்."
    if language == "hi":
        return "नमस्ते! मैं कैसे मदद करूँ? सेवा और स्थान बताइए।"
    if language == "te":
        return "నమస్కారం! మీకు ఏ సహాయం కావాలి? సేవ పేరు మరియు ప్రాంతం చెప్పండి."
    if language == "ml":
        return "നമസ്കാരം! നിങ്ങള്‍ക്ക് എന്ത് സഹായം വേണം? സേവനവും സ്ഥലവും പറയൂ."
    if language == "kn":
        return "ನಮಸ್ಕಾರ! ನಿಮಗೆ ಏನು ಸಹಾಯ ಬೇಕು? ಸೇವೆ ಮತ್ತು ಸ್ಥಳವನ್ನು ತಿಳಿಸಿ."
    if language == "mr":
        return "नमस्कार! तुम्हाला कोणती मदत हवी? सेवा आणि स्थान सांगा."
    if language == "bn":
        return "নমস্কার! কী সাহায্য দরকার? সেবা এবং অবস্থান বলুন।"
    return "Hi! How can I help you today? Tell me your service and location."


def _thanks_reply(language):
    if language == "ta":
        return "நன்றி! வேறு உதவி வேண்டுமா? நான் உதவ தயாராக உள்ளேன்."
    if language == "hi":
        return "धन्यवाद! अगर और मदद चाहिए तो बताइए।"
    if language == "te":
        return "ధన్యవాదాలు! ఇంకేమైనా సహాయం కావాలంటే చెప్పండి."
    if language == "ml":
        return "നന്ദി! ഇനി സഹായം വേണമെങ്കിൽ പറഞ്ഞോളൂ."
    if language == "kn":
        return "ಧನ್ಯವಾದ! ಇನ್ನೂ ಸಹಾಯ ಬೇಕಿದ್ದರೆ ತಿಳಿಸಿ."
    if language == "mr":
        return "धन्यवाद! आणखी मदत हवी असल्यास सांगा."
    if language == "bn":
        return "ধন্যবাদ! আরও সাহায্য দরকার হলে বলুন।"
    return "You are welcome. If you need anything else, I am here to help."


def _service_queryset():
    return Service.objects.filter(is_active=True)


def _infer_service(text):
    normalized = _normalize_text(text)
    if not normalized:
        return None

    # Aadhaar queries are handled by dedicated reply logic; do not auto-map to Post Office.
    if "aadhaar" in normalized or "aadhar" in normalized:
        return None

    for service in _service_queryset():
        code = (service.code or "").lower()
        name = (service.name or "").lower()
        if code and code in normalized:
            return service
        if name and name in normalized:
            return service

    for label, keywords in SERVICE_HINTS.items():
        if any(keyword in normalized for keyword in keywords):
            for service in _service_queryset():
                name = (service.name or "").lower()
                code = (service.code or "").lower()
                if label in name or label in code:
                    return service
    return None


def _extract_user_location(content):
    raw_text = content or ""
    normalized = _normalize_text(raw_text)

    lat = lon = None
    lat_lon_match = LAT_LON_PATTERN.search(raw_text)
    if not lat_lon_match:
        lat_lon_match = LAT_LON_PATTERN.search(raw_text.lower())
    if lat_lon_match:
        try:
            lat = float(lat_lon_match.group(1))
            lon = float(lat_lon_match.group(2))
        except (TypeError, ValueError):
            lat = lon = None

    location_text = ""
    split_match = LOCATION_SPLIT_PATTERN.search(normalized)
    if split_match:
        location_text = (split_match.group(1) or "").strip()
        location_text = location_text.replace("near me", "").strip()

    return lat, lon, location_text


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _pick_nearby_offices(service, content):
    offices = list(Office.objects.filter(service=service, is_active=True))
    lat, lon, location_text = _extract_user_location(content)

    if lat is not None and lon is not None:
        offices_with_distance = []
        for office in offices:
            if office.latitude is None or office.longitude is None:
                continue
            km = _distance_km(lat, lon, float(office.latitude), float(office.longitude))
            offices_with_distance.append((km, office))
        if offices_with_distance:
            offices_with_distance.sort(key=lambda row: row[0])
            return [row[1] for row in offices_with_distance[:3]], "coords"
        return [], "coords_no_data"

    if location_text:
        city_matches = [o for o in offices if location_text in (o.city or "").lower()]
        if city_matches:
            city_matches.sort(key=lambda o: ((o.city or ""), (o.name or "")))
            return city_matches[:3], "city"
        return [], "city_no_match"

    offices.sort(key=lambda o: ((o.city or ""), (o.name or "")))
    return offices[:3], "fallback"


def _format_office_reply(service, language, content):
    offices, mode = _pick_nearby_offices(service, content)
    if mode == "coords_no_data":
        map_link = _maps_nearby_link(service, content)
        if language == "ta":
            return f"இப்போது GPS அடிப்படையிலான அலுவலக பதிவுகள் இல்லை. அருகிலுள்ள மேப் தேடல்: {map_link}"
        if language == "hi":
            return f"GPS के आधार पर कार्यालय डेटा उपलब्ध नहीं है। नजदीकी मैप खोज: {map_link}"
        if language == "te":
            return f"GPS ఆధారిత కార్యాలయ సమాచారం లేదు. సమీప మ్యాప్ శోధన: {map_link}"
        if language == "ml":
            return f"GPS അടിസ്ഥാനത്തിലുള്ള ഓഫീസ് വിവരങ്ങൾ ലഭ്യമല്ല. സമീപ മാപ്പ് തിരയൽ: {map_link}"
        if language == "kn":
            return f"GPS ಆಧಾರಿತ ಕಚೇರಿ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ಹತ್ತಿರದ ಮ್ಯಾಪ್ ಹುಡುಕಾಟ: {map_link}"
        if language == "mr":
            return f"GPS आधारित कार्यालय माहिती उपलब्ध नाही. जवळचा मॅप शोध: {map_link}"
        if language == "bn":
            return f"GPS ভিত্তিক অফিস তথ্য নেই। কাছাকাছি ম্যাপ সার্চ: {map_link}"
        return f"I could not find geo-tagged {service.name} offices in local data for your exact GPS. Use nearby map search: {map_link}"

    if mode == "city_no_match":
        map_link = _maps_nearby_link(service, content)
        if language == "ta":
            return f"அந்த பகுதி உள்ளூர் அலுவலக தரவுடன் பொருந்தவில்லை. அருகிலுள்ள மேப் தேடல்: {map_link}"
        if language == "hi":
            return f"उस क्षेत्र का मेल नहीं मिला। नजदीकी मैप खोज: {map_link}"
        if language == "te":
            return f"ఆ ప్రాంతం స్థానిక డేటాతో సరిపోలలేదు. సమీప మ్యాప్ శోధన: {map_link}"
        if language == "ml":
            return f"ആ പ്രദേശം ലോക്കൽ ഡേറ്റയിൽ ഇല്ല. സമീപ മാപ്പ് തിരയൽ: {map_link}"
        if language == "kn":
            return f"ಆ ಪ್ರದೇಶ ಸ್ಥಳೀಯ ಡೇಟಾದಲ್ಲಿ ಹೊಂದಿಕೆಯಾಗಲಿಲ್ಲ. ಹತ್ತಿರದ ಮ್ಯಾಪ್ ಹುಡುಕಾಟ: {map_link}"
        if language == "mr":
            return f"त्या भागाची माहिती मिळाली नाही. जवळचा मॅप शोध: {map_link}"
        if language == "bn":
            return f"ওই এলাকার তথ্য পাওয়া যায়নি। কাছাকাছি ম্যাপ সার্চ: {map_link}"
        return f"I could not match that area in local office data. Use nearby map search: {map_link}"

    if not offices:
        if language == "ta":
            return f"{service.name} அலுவலக விவரங்கள் இன்னும் இல்லை. உங்கள் பகுதியை கூறுங்கள்."
        if language == "hi":
            return f"{service.name} के कार्यालय विवरण उपलब्ध नहीं हैं। अपना स्थान बताइए।"
        if language == "te":
            return f"{service.name} కార్యాలయ వివరాలు లేవు. మీ ప్రాంతాన్ని చెప్పండి."
        if language == "ml":
            return f"{service.name} ഓഫീസ് വിവരങ്ങൾ ലഭ്യമല്ല. നിങ്ങളുടെ സ്ഥലം പറയൂ."
        if language == "kn":
            return f"{service.name} ಕಚೇರಿ ವಿವರಗಳು ಲಭ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ಹೇಳಿ."
        if language == "mr":
            return f"{service.name} कार्यालयांची माहिती नाही. तुमचे स्थान सांगा."
        if language == "bn":
            return f"{service.name} অফিসের তথ্য নেই। আপনার অবস্থান বলুন।"
        return f"No office listing yet for {service.name}. Share your area and I will guide you."

    if language == "ta":
        lines = [f"{service.name} அருகிலுள்ள அலுவலகங்கள்:"]
    elif language == "hi":
        lines = [f"{service.name} के नजदीकी कार्यालय:"]
    elif language == "te":
        lines = [f"{service.name} సమీప కార్యాలయాలు:"]
    elif language == "ml":
        lines = [f"{service.name} സമീപ ഓഫിസുകൾ:"]
    elif language == "kn":
        lines = [f"{service.name} ಹತ್ತಿರದ ಕಚೇರಿಗಳು:"]
    elif language == "mr":
        lines = [f"{service.name} जवळची कार्यालये:"]
    elif language == "bn":
        lines = [f"{service.name} নিকটবর্তী অফিসগুলো:"]
    else:
        lines = [f"Nearest {service.name} offices:"]
    if mode == "fallback":
        if language == "ta":
            lines.append("தற்போதைய இருப்பிடம் சரியாகப் பொருந்தவில்லை; கிடைக்கும் அலுவலகங்களை பகிர்கிறேன்.")
        elif language == "hi":
            lines.append("आपका स्थान ठीक से नहीं मिला, उपलब्ध कार्यालय साझा कर रहा हूँ।")
        elif language == "te":
            lines.append("మీ స్థానం సరిగా సరిపోలలేదు; అందుబాటులో ఉన్న కార్యాలయాలను చూపుతున్నాను.")
        elif language == "ml":
            lines.append("നിങ്ങളുടെ സ്ഥലം കൃത്യമായി ലഭ്യമല്ല; ലഭ്യമായ ഓഫിസുകൾ നൽകുന്നു.")
        elif language == "kn":
            lines.append("ನಿಮ್ಮ ಸ್ಥಳ ಸರಿಯಾಗಿ ಹೊಂದಿಕೆಯಾಗಲಿಲ್ಲ; ಲಭ್ಯ ಕಚೇರಿಗಳನ್ನು ನೀಡುತ್ತಿದ್ದೇನೆ.")
        elif language == "mr":
            lines.append("तुमचे स्थान अचूक जुळले नाही; उपलब्ध कार्यालये देत आहे.")
        elif language == "bn":
            lines.append("আপনার অবস্থান সঠিকভাবে মেলেনি, উপলব্ধ অফিস দিচ্ছি।")
        else:
            lines.append("I could not match your current location exactly, so sharing available offices.")

    for office in offices:
        segment = f"- {office.name}, {office.city}"
        if office.timings:
            if language == "ta":
                segment += f" | நேரம்: {office.timings}"
            elif language == "hi":
                segment += f" | समय: {office.timings}"
            elif language == "te":
                segment += f" | సమయం: {office.timings}"
            elif language == "ml":
                segment += f" | സമയം: {office.timings}"
            elif language == "kn":
                segment += f" | ಸಮಯ: {office.timings}"
            elif language == "mr":
                segment += f" | वेळ: {office.timings}"
            elif language == "bn":
                segment += f" | সময়: {office.timings}"
            else:
                segment += f" | Timings: {office.timings}"
        if office.contact_phone:
            if language == "ta":
                segment += f" | தொலைபேசி: {office.contact_phone}"
            elif language == "hi":
                segment += f" | फ़ोन: {office.contact_phone}"
            elif language == "te":
                segment += f" | ఫోన్: {office.contact_phone}"
            elif language == "ml":
                segment += f" | ഫോൺ: {office.contact_phone}"
            elif language == "kn":
                segment += f" | ಫೋನ್: {office.contact_phone}"
            elif language == "mr":
                segment += f" | फोन: {office.contact_phone}"
            elif language == "bn":
                segment += f" | ফোন: {office.contact_phone}"
            else:
                segment += f" | Phone: {office.contact_phone}"
        query = f"{office.name} {office.address or ''} {office.city or ''}".strip()
        generated_map_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
        map_link = office.google_map_link or generated_map_link
        if language == "ta":
            segment += f" | வரைபடம்: {map_link}"
        elif language == "hi":
            segment += f" | मानचित्र: {map_link}"
        elif language == "te":
            segment += f" | మ్యాప్: {map_link}"
        elif language == "ml":
            segment += f" | മാപ്പ്: {map_link}"
        elif language == "kn":
            segment += f" | ಮ್ಯಾಪ್: {map_link}"
        elif language == "mr":
            segment += f" | नकाशा: {map_link}"
        elif language == "bn":
            segment += f" | মানচিত্র: {map_link}"
        else:
            segment += f" | Map: {map_link}"
        lines.append(segment)
    return "\n".join(lines)


def _format_documents_reply(service, language):
    docs = DocumentsRequired.objects.filter(service=service, is_active=True, language=language).order_by("id")
    if not docs.exists() and language != "en":
        docs = DocumentsRequired.objects.filter(service=service, is_active=True, language="en").order_by("id")

    if not docs.exists():
        if language == "ta":
            return f"{service.name} ஆவண பட்டியல் இன்னும் இல்லை. உங்கள் கோரிக்கையை தெளிவாக கூறுங்கள்."
        if language == "hi":
            return f"{service.name} के लिए दस्तावेज़ सूची उपलब्ध नहीं है। अपना अनुरोध स्पष्ट बताइए।"
        if language == "te":
            return f"{service.name} కోసం పత్రాల జాబితా లేదు. మీ అభ్యర్థన స్పష్టంగా చెప్పండి."
        if language == "ml":
            return f"{service.name} നുള്ള രേഖ പട്ടിക ലഭ്യമല്ല. അഭ്യർത്ഥന വ്യക്തമാക്കൂ."
        if language == "kn":
            return f"{service.name}ಗಾಗಿ ದಾಖಲೆ ಪಟ್ಟಿ ಲಭ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಬೇಡಿಕೆಯನ್ನು ಸ್ಪಷ್ಟಪಡಿಸಿ."
        if language == "mr":
            return f"{service.name} साठी कागदपत्रांची यादी उपलब्ध नाही. तुमची मागणी स्पष्ट करा."
        if language == "bn":
            return f"{service.name} এর জন্য নথির তালিকা নেই। আপনার অনুরোধ স্পষ্ট করুন।"
        return f"Document checklist is not configured yet for {service.name}. Tell me the exact service request."

    if language == "ta":
        head = f"{service.name}க்கு தேவையான ஆவணங்கள்:"
    elif language == "hi":
        head = f"{service.name} के लिए आवश्यक दस्तावेज़:"
    elif language == "te":
        head = f"{service.name} కోసం అవసరమైన పత్రాలు:"
    elif language == "ml":
        head = f"{service.name}ക്ക് ആവശ്യമായ രേഖകൾ:"
    elif language == "kn":
        head = f"{service.name}ಗೆ ಅಗತ್ಯ ದಾಖಲೆಗಳು:"
    elif language == "mr":
        head = f"{service.name} साठी आवश्यक कागदपत्रे:"
    elif language == "bn":
        head = f"{service.name} এর জন্য প্রয়োজনীয় নথি:"
    else:
        head = f"Documents required for {service.name}:"
    lines = [head]
    for doc in docs[:3]:
        lines.append(f"- {doc.title}: {doc.details}")
    return "\n".join(lines)


def find_kb_answer(service, text, language, session=None):
    qs = KnowledgeBase.objects.filter(is_active=True, language=language)
    if service:
        qs = qs.filter(Q(service=service) | Q(service__isnull=True))
    else:
        qs = qs.filter(service__isnull=True)

    history = get_session_history(session, limit=6)
    search_query = build_search_query(text, history)

    best_entry = None
    best_score = 0
    normalized_text = _normalize_text(search_query)
    for entry in qs.order_by("priority", "id"):
        score = _keyword_score(entry.keywords, normalized_text)
        if entry.question and _normalize_text(entry.question) in normalized_text:
            score += 2
        if score > best_score:
            best_score = score
            best_entry = entry

    MIN_KB_SCORE = 2
    if best_entry and best_score >= MIN_KB_SCORE:
        return best_entry.answer
    builtin = _builtin_qa_answer(service, search_query, language)
    if builtin:
        return builtin

    try:
        from .ai_responder import generate_response

        history = get_session_history(session, limit=6)
        formatted_history = []
        for item in history:
            role = item.get("role", "Citizen").lower()
            formatted_history.append(
                {
                    "role": "assistant" if role in {"assistant", "bot"} else "user",
                    "content": item.get("content", ""),
                }
            )

        result = generate_response(
            user_message=search_query,
            session_history=formatted_history,
            user_language=language,
        )
        return result.get("response") or None
    except Exception:
        return None


def needs_escalation(text):
    lowered = (text or "").lower()
    return any(token in lowered for token in ["agent", "human", "escalate", "officer", "representative", "connect", "admin", "person"])


def _pick_agent():
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(Q(role="ADMIN") | Q(is_staff=True) | Q(is_superuser=True)).order_by("id").first()


def _create_notification(user, title, message, link="/civic/"):
    if user and getattr(user, "is_active", False):
        CivicNotification.objects.create(
            user=user,
            title=title,
            message=message,
            link=link,
            is_read=False,
        )


def _fallback_reply(language, variant=0):
    reply_map = {
        "ta": [
            "நான் உதவ தயாராக இருக்கிறேன். சேவை பெயரும் இடமும் சொல்லுங்கள்.",
            "சேவை, இடம், உங்கள் வேண்டுகோளை பகிருங்கள்.",
            "உதாரணம்: 'EB payment Chennai' அல்லது 'Ration card documents Madurai'.",
        ],
        "hi": [
            "मैं मदद के लिए तैयार हूँ। सेवा और स्थान बताइए।",
            "सेवा, स्थान और आपका अनुरोध बताइए।",
            "उदाहरण: 'EB bill payment Chennai' या 'Ration card documents Madurai'.",
        ],
        "te": [
            "నేను సహాయానికి సిద్ధంగా ఉన్నాను. సేవ పేరు మరియు ప్రాంతం చెప్పండి.",
            "సేవ, ప్రాంతం మరియు మీ అవసరాన్ని చెప్పండి.",
            "ఉదాహరణ: 'EB bill payment Chennai' లేదా 'Ration card documents Madurai'.",
        ],
        "ml": [
            "ഞാന്‍ സഹായിക്കാന്‍ തയ്യാറാണ്. സേവനവും സ്ഥലവും പറയൂ.",
            "സേവനം, സ്ഥലം, നിങ്ങൾക്ക് വേണ്ടത് വ്യക്തമാക്കൂ.",
            "ഉദാഹരണം: 'EB bill payment Chennai' അല്ലെങ്കിൽ 'Ration card documents Madurai'.",
        ],
        "kn": [
            "ನಾನು ಸಹಾಯಕ್ಕೆ ಸಿದ್ಧನಿದ್ದೇನೆ. ಸೇವೆ ಮತ್ತು ಸ್ಥಳ ತಿಳಿಸಿ.",
            "ಸೇವೆ, ಸ್ಥಳ ಮತ್ತು ನಿಮ್ಮ ಅಗತ್ಯವನ್ನು ಹೇಳಿ.",
            "ಉದಾಹರಣೆ: 'EB bill payment Chennai' ಅಥವಾ 'Ration card documents Madurai'.",
        ],
        "mr": [
            "मी मदतीस तयार आहे. सेवा आणि स्थान सांगा.",
            "सेवा, स्थान आणि तुम्हाला नेमके काय हवे आहे ते सांगा.",
            "उदाहरण: 'EB bill payment Chennai' किंवा 'Ration card documents Madurai'.",
        ],
        "bn": [
            "আমি সাহায্যের জন্য প্রস্তুত। সেবা এবং অবস্থান বলুন।",
            "সেবা, অবস্থান এবং কী প্রয়োজন তা বলুন।",
            "উদাহরণ: 'EB bill payment Chennai' অথবা 'Ration card documents Madurai'.",
        ],
        "en": [
            "I can help with Post Office, Electricity Board, Bank, and Government services. Share your service and area.",
            "Tell me what you need: office timings, required documents, nearest office, bill/payment help, or complaint tracking.",
            "Try this format: '<service> + <location> + <need>' (example: 'EB bill payment in Chennai').",
        ],
    }
    pool = reply_map.get(language) or reply_map["en"]
    return pool[variant % len(pool)]


def _service_specific_reply(service, intent, content, language):
    if not service:
        return None
    service_name = (service.name or "").lower()
    query = _normalize_text(content)

    is_post = "post" in service_name
    is_eb = "electric" in service_name or "eb" in service_name
    is_bank = "bank" in service_name
    is_govt = "gov" in service_name or "government" in service_name

    if intent == "payment" or ("online" in query and any(k in query for k in ["pay", "payment", "bill"])):
        if is_eb:
            if language == "ta":
                return (
                    "EB கட்டணம் ஆன்லைன் செலுத்த: 1) அதிகாரப்பூர்வ இணையதளம்/அப் திறக்கவும், "
                    "2) சேவை எண் உள்ளிடவும், 3) தொகையை சரிபார்க்கவும், 4) UPI/கார்டு/நெட் பேங்கிங் மூலம் செலுத்தவும், "
                    "5) ரசீதை சேமிக்கவும்."
                )
            if language == "hi":
                return (
                    "EB बिल ऑनलाइन भुगतान: 1) आधिकारिक पोर्टल/ऐप खोलें, "
                    "2) सेवा/उपभोक्ता नंबर डालें, 3) राशि सत्यापित करें, 4) UPI/कार्ड/नेटबैंकिंग से भुगतान करें, "
                    "5) रसीद/ट्रांजैक्शन आईडी सहेजें।"
                )
            if language == "te":
                return (
                    "EB బిల్ ఆన్‌లైన్ చెల్లింపు: 1) అధికారిక పోర్టల్/యాప్ తెరవండి, "
                    "2) సేవ/కన్స్యూమర్ నంబర్ నమోదు చేయండి, 3) మొత్తాన్ని ధృవీకరించండి, 4) UPI/కార్డ్/నెట్‌బ్యాంకింగ్ ద్వారా చెల్లించండి, "
                    "5) రసీదును సేవ్ చేయండి."
                )
            if language == "ml":
                return (
                    "EB ബിൽ ഓൺലൈൻ പേയ്‌മെന്റ്: 1) ഔദ്യോഗിക പോർട്ടൽ/ആപ്പ് തുറക്കുക, "
                    "2) സർവീസ്/കൺസ്യൂമർ നമ്പർ നൽകുക, 3) തുക സ്ഥിരീകരിക്കുക, 4) UPI/കാർഡ്/നെറ്റ് ബാങ്കിംഗ് വഴി പേയ് ചെയ്യുക, "
                    "5) രസീദ് സേവ് ചെയ്യുക."
                )
            if language == "kn":
                return (
                    "EB ಬಿಲ್ ಆನ್‌ಲೈನ್ ಪಾವತಿ: 1) ಅಧಿಕೃತ ಪೋರ್ಟಲ್/ಆಪ್ ತೆರೆಯಿರಿ, "
                    "2) ಸೇವೆ/ಗ್ರಾಹಕ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ, 3) ಮೊತ್ತ ಪರಿಶೀಲಿಸಿ, 4) UPI/ಕಾರ್ಡ್/ನೇಟ್ ಬ್ಯಾಂಕಿಂಗ್ ಮೂಲಕ ಪಾವತಿಸಿ, "
                    "5) ರಸೀದಿ ಉಳಿಸಿ."
                )
            if language == "mr":
                return (
                    "EB बिल ऑनलाइन पेमेंट: 1) अधिकृत पोर्टल/अॅप उघडा, "
                    "2) सेवा/ग्राहक क्रमांक टाका, 3) रक्कम तपासा, 4) UPI/कार्ड/नेटबँकिंगने पेमेंट करा, "
                    "5) पावती जतन करा."
                )
            if language == "bn":
                return (
                    "EB বিল অনলাইন পেমেন্ট: 1) অফিসিয়াল পোর্টাল/অ্যাপ খুলুন, "
                    "2) সার্ভিস/কনজিউমার নম্বর দিন, 3) পরিমাণ যাচাই করুন, 4) UPI/কার্ড/নেট ব্যাঙ্কিং দিয়ে পেমেন্ট করুন, "
                    "5) রসিদ সংরক্ষণ করুন।"
                )
            return (
                "For EB bill payment online: 1) Open official electricity board portal/app, "
                "2) Enter service/consumer number, 3) Verify due amount, 4) Pay via UPI/card/netbanking, "
                "5) Save receipt or transaction ID for tracking."
            )
        if is_post:
            if language == "ta":
                return "போஸ்ட் ஆபிஸ் கட்டணங்களுக்கு அதிகாரப்பூர்வ India Post சேவைகளை பயன்படுத்தவும் அல்லது அருகிலுள்ள கிளைக்கு செல்லவும்."
            if language == "hi":
                return "पोस्ट ऑफिस भुगतान के लिए India Post के आधिकारिक चैनल उपयोग करें या नजदीकी शाखा जाएं।"
            if language == "te":
                return "పోస్ట్ ఆఫీస్ చెల్లింపులకు అధికారిక India Post ఛానెల్స్ ఉపయోగించండి లేదా సమీప శాఖకు వెళ్లండి."
            if language == "ml":
                return "പോസ്റ്റ് ഓഫീസ് പേയ്‌മെന്റുകൾക്കായി ഔദ്യോഗിക India Post സേവനങ്ങൾ ഉപയോഗിക്കുക അല്ലെങ്കിൽ സമീപ ശാഖ സന്ദർശിക്കുക."
            if language == "kn":
                return "ಪೋಸ್ಟ್ ಆಫೀಸ್ ಪಾವತಿಗಳಿಗೆ ಅಧಿಕೃತ India Post ಸೇವೆಗಳನ್ನು ಬಳಸಿ ಅಥವಾ ಹತ್ತಿರದ ಶಾಖೆಗೆ ಹೋಗಿ."
            if language == "mr":
                return "पोस्ट ऑफिस पेमेंटसाठी अधिकृत India Post चॅनेल वापरा किंवा जवळच्या शाखेत जा."
            if language == "bn":
                return "পোস্ট অফিস পেমেন্টের জন্য অফিসিয়াল India Post চ্যানেল ব্যবহার করুন অথবা নিকটবর্তী শাখায় যান।"
            return (
                "For Post Office payments, use official India Post channels where available or visit the nearest branch "
                "with account/booking reference details."
            )
        if is_bank:
            if language == "ta":
                return "வங்கி கட்டணங்களுக்கு அதிகாரப்பூர்வ மொபைல்/நெட் பேங்கிங் பயன்படுத்தி, ரசீதை சேமிக்கவும்."
            if language == "hi":
                return "बैंक भुगतान के लिए आधिकारिक मोबाइल/नेट बैंकिंग का उपयोग करें और रसीद सुरक्षित रखें।"
            if language == "te":
                return "బ్యాంక్ చెల్లింపులకు అధికారిక మొబైల్/నెట్ బ్యాంకింగ్ ఉపయోగించి రసీదును సేవ్ చేయండి."
            if language == "ml":
                return "ബാങ്ക് പേയ്‌മെന്റുകൾക്കായി ഔദ്യോഗിക മൊബൈൽ/നെറ്റ് ബാങ്കിംഗ് ഉപയോഗിച്ച് രസീദ് സൂക്ഷിക്കുക."
            if language == "kn":
                return "ಬ್ಯಾಂಕ್ ಪಾವತಿಗಳಿಗೆ ಅಧಿಕೃತ ಮೊಬೈಲ್/ನೇಟ್ ಬ್ಯಾಂಕಿಂಗ್ ಬಳಸಿ, ರಸೀದಿ ಉಳಿಸಿ."
            if language == "mr":
                return "बँक पेमेंटसाठी अधिकृत मोबाइल/नेट बँकिंग वापरा आणि पावती जतन करा."
            if language == "bn":
                return "ব্যাংক পেমেন্টের জন্য অফিসিয়াল মোবাইল/নেট ব্যাংকিং ব্যবহার করে রসিদ সংরক্ষণ করুন।"
            return (
                "For bank payments, use official mobile/internet banking with account and OTP verification, then save the receipt reference."
            )

    if intent == "documents":
        if is_govt and "passport" in query:
            if language == "ta":
                return "பாஸ்போர்ட் ஆவணங்களில் பொதுவாக ID proof, address proof, DOB proof மற்றும் புகைப்படம் தேவை."
            if language == "hi":
                return "पासपोर्ट दस्तावेज़ में आम तौर पर ID proof, address proof, DOB proof और फोटो चाहिए।"
            if language == "te":
                return "పాస్‌పోర్ట్ కోసం సాధారణంగా ID, address, DOB proof మరియు ఫోటో అవసరం."
            if language == "ml":
                return "പാസ്‌പോർട്ടിന് സാധാരണയായി ID, വിലാസം, DOB തെളിവ്, ഫോട്ടോ ആവശ്യമാണ്."
            if language == "kn":
                return "ಪಾಸ್‌ಪೋರ್ಟ್‌ಗೆ ಸಾಮಾನ್ಯವಾಗಿ ID, ವಿಳಾಸ, DOB ಪುರಾವೆ ಮತ್ತು ಫೋಟೋ ಬೇಕು."
            if language == "mr":
                return "पासपोर्टसाठी साधारणपणे ID, पत्ता, DOB पुरावा आणि फोटो आवश्यक असतात."
            if language == "bn":
                return "পাসপোর্টের জন্য সাধারণত ID, ঠিকানা, DOB প্রমাণ এবং ছবি লাগে।"
            return "Passport documents typically include ID proof, address proof, date-of-birth proof, and passport photos as per Passport Seva guidelines."
        if is_govt and "license" in query:
            if language == "ta":
                return "டிரைவிங் லைசன்ஸுக்கு பொதுவாக வயது சான்று, முகவரி சான்று, லேர்னர் லைசன்ஸ் விவரங்கள், புகைப்படம் தேவை."
            if language == "hi":
                return "ड्राइविंग लाइसेंस के लिए आम तौर पर आयु प्रमाण, पता प्रमाण, लर्नर लाइसेंस विवरण और फोटो चाहिए।"
            if language == "te":
                return "డ్రైవింగ్ లైసెన్స్‌కు వయస్సు, చిరునామా రుజువు, లెర్నర్ వివరాలు, ఫోటో అవసరం."
            if language == "ml":
                return "ഡ്രൈവിംഗ് ലൈസൻസിന് വയസ്, വിലാസം തെളിവ്, ലേണർ വിവരങ്ങൾ, ഫോട്ടോ ആവശ്യമാണ്."
            if language == "kn":
                return "ಡ್ರೈವಿಂಗ್ ಲೈಸನ್ಸ್‌ಗೆ ವಯಸ್ಸು, ವಿಳಾಸ ಪುರಾವೆ, ಲರ್ನರ್ ವಿವರಗಳು, ಫೋಟೋ ಅಗತ್ಯ."
            if language == "mr":
                return "ड्रायव्हिंग लायसन्ससाठी वय, पत्ता पुरावा, लर्नर तपशील आणि फोटो लागतात."
            if language == "bn":
                return "ড্রাইভিং লাইসেন্সের জন্য বয়স, ঠিকানা প্রমাণ, লার্নার ডিটেলস এবং ছবি প্রয়োজন।"
            return "Driving license documents usually include age proof, address proof, learner license details, and passport-size photos."
        if is_govt and "visa" in query:
            if language == "ta":
                return "விசா ஆவணங்கள் நாட்டைப் பொறுத்தது; பொதுவாக பாஸ்போர்ட், புகைப்படம், நிதி சான்று, பயண விவரம் தேவை."
            if language == "hi":
                return "वीजा दस्तावेज़ देश पर निर्भर करते हैं; सामान्यतः पासपोर्ट, फोटो, वित्तीय प्रमाण, यात्रा विवरण चाहिए।"
            if language == "te":
                return "వీసా పత్రాలు దేశం మీద ఆధారపడి ఉంటాయి; సాధారణంగా పాస్‌పోర్ట్, ఫోటోలు, ఆర్థిక ఆధారాలు, ప్రయాణ వివరాలు అవసరం."
            if language == "ml":
                return "വിസ ഡോക്യുമെന്റുകൾ രാജ്യത്തെ ആശ്രയിക്കുന്നു; സാധാരണയായി പാസ്‌പോർട്ട്, ഫോട്ടോകൾ, സാമ്പത്തിക തെളിവ്, യാത്ര വിവരങ്ങൾ ആവശ്യമാണ്."
            if language == "kn":
                return "ವೀಸಾ ದಾಖಲೆಗಳು ದೇಶದ ಮೇಲೆ ಅವಲಂಬಿತ; ಸಾಮಾನ್ಯವಾಗಿ ಪಾಸ್‌ಪೋರ್ಟ್, ಫೋಟೋ, ಹಣಕಾಸು ಪುರಾವೆ, ಪ್ರಯಾಣ ವಿವರಗಳು ಬೇಕು."
            if language == "mr":
                return "व्हिसा कागदपत्रे देशानुसार बदलतात; साधारणपणे पासपोर्ट, फोटो, आर्थिक पुरावा, प्रवास तपशील लागतो."
            if language == "bn":
                return "ভিসার নথি দেশভেদে পরিবর্তিত; সাধারণত পাসপোর্ট, ছবি, আর্থিক প্রমাণ, ভ্রমণ তথ্য লাগে।"
            return "Visa documents vary by country, but usually include passport, photos, financial proof, itinerary, and purpose-specific supporting documents."

    if intent == "timings":
        if language == "ta":
            return f"{service.name} அலுவலக நேரம் அருகிலுள்ள அலுவலகங்களிலிருந்து வழங்க முடியும். உங்கள் இடத்தை பகிருங்கள்."
        if language == "hi":
            return f"{service.name} के कार्यालय समय देने के लिए अपना स्थान बताइए।"
        if language == "te":
            return f"{service.name} కార్యాలయ సమయాల కోసం మీ స్థానం చెప్పండి."
        if language == "ml":
            return f"{service.name} ഓഫീസ് സമയം നൽകാൻ നിങ്ങളുടെ സ്ഥലം പങ്കിടുക."
        if language == "kn":
            return f"{service.name} ಕಚೇರಿ ಸಮಯಕ್ಕಾಗಿ ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ತಿಳಿಸಿ."
        if language == "mr":
            return f"{service.name} कार्यालय वेळांसाठी तुमचे स्थान सांगा."
        if language == "bn":
            return f"{service.name} অফিস সময়ের জন্য আপনার অবস্থান দিন।"
        return f"I can provide {service.name} office timings from nearby offices. Share your location or tap location button for accurate results."

    return None


def _aadhaar_specific_reply(content, language):
    query = _normalize_text(content)
    if "aadhaar" not in query and "aadhar" not in query:
        return None

    if any(token in query for token in ["document", "documents", "proof", "renew", "update", "correction", "change"]):
        if language == "ta":
            return (
                "ஆதார் புதுப்பிப்புக்கு: 1) ஆதார் எண்/நகல், 2) செல்லுபடி ID சான்று, "
                "3) முகவரி சான்று (முகவரி மாற்றம் என்றால்), 4) திருத்த ஆதாரம், 5) OTPக்கு மொபைல் எண். "
                "Aadhaar Seva Kendra அல்லது அங்கீகார மையத்தில் செய்யலாம்."
            )
        if language == "hi":
            return (
                "आधार अपडेट के लिए: 1) आधार नंबर/कॉपी, 2) वैध ID, "
                "3) पता प्रमाण (यदि पता बदले), 4) सुधार का समर्थन दस्तावेज़, 5) OTP के लिए मोबाइल नंबर। "
                "Aadhaar Seva Kendra या अधिकृत केंद्र में कर सकते हैं."
            )
        if language == "te":
            return (
                "ఆధార్ అప్డేట్ కోసం: 1) ఆధార్ నంబర్/కాపీ, 2) చెల్లుబాటు అయ్యే ID, "
                "3) చిరునామా రుజువు (చిరునామా మారితే), 4) సరిదిద్దడానికి ఆధార పత్రం, 5) OTP కోసం మొబైల్ నంబర్. "
                "Aadhaar Seva Kendra లేదా అధీకృత కేంద్రంలో చేయవచ్చు."
            )
        if language == "ml":
            return (
                "ആധാർ അപ്‌ഡേറ്റ് ചെയ്യാൻ: 1) ആധാർ നമ്പർ/കോപി, 2) സാധുവായ ID, "
                "3) വിലാസ തെളിവ് (വിലാസം മാറ്റുന്നുവെങ്കിൽ), 4) തിരുത്തൽ പിന്തുണ രേഖ, 5) OTPയ്ക്ക് മൊബൈൽ നമ്പർ. "
                "Aadhaar Seva Kendra അല്ലെങ്കിൽ അംഗീകൃത കേന്ദ്രത്തിൽ ചെയ്യാം."
            )
        if language == "kn":
            return (
                "ಆಧಾರ್ ಅಪ್‌ಡೇಟಿಗಾಗಿ: 1) ಆಧಾರ್ ಸಂಖ್ಯೆ/ನಕಲು, 2) ಮಾನ್ಯ ID, "
                "3) ವಿಳಾಸ ಪುರಾವೆ (ವಿಳಾಸ ಬದಲಾವಣೆಗೆ), 4) ತಿದ್ದುಪಡಿ ಪುರಾವೆ, 5) OTPಗೆ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ. "
                "Aadhaar Seva Kendra ಅಥವಾ ಅಧಿಕೃತ ಕೇಂದ್ರದಲ್ಲಿ ಮಾಡಬಹುದು."
            )
        if language == "mr":
            return (
                "आधार अपडेटसाठी: 1) आधार नंबर/कॉपी, 2) वैध ID, "
                "3) पत्ता पुरावा (पत्ता बदलल्यास), 4) दुरुस्तीचा पुरावा, 5) OTP साठी मोबाइल नंबर. "
                "Aadhaar Seva Kendra किंवा अधिकृत केंद्रात करता येते."
            )
        if language == "bn":
            return (
                "আধার আপডেটের জন্য: 1) আধার নম্বর/কপি, 2) বৈধ ID, "
                "3) ঠিকানার প্রমাণ (ঠিকানা পরিবর্তন হলে), 4) সংশোধনের সহায়ক নথি, 5) OTP-এর জন্য মোবাইল নম্বর। "
                "Aadhaar Seva Kendra বা অনুমোদিত কেন্দ্রে করা যায়।"
            )
        return (
            "For Aadhaar update/renewal, keep these ready: "
            "1) Aadhaar number/card copy, "
            "2) valid ID proof, "
            "3) address proof (if address change), "
            "4) supporting document for requested correction, "
            "5) mobile number for OTP/updates. "
            "You can complete this at an Aadhaar Seva Kendra or authorized update center."
        )

    if language == "ta":
        return "ஆதார் உதவிக்காக: பெயர்/DOB திருத்தம், முகவரி அப்டேட், மொபைல் அப்டேட், அல்லது மையம் தேடல் என்று சொல்லுங்கள்."
    if language == "hi":
        return "आधार सहायता के लिए: नाम/DOB सुधार, पता अपडेट, मोबाइल अपडेट या केंद्र स्थान बताइए।"
    if language == "te":
        return "ఆధార్ సహాయం కోసం: పేరు/DOB సవరణ, చిరునామా అప్‌డేట్, మొబైల్ అప్‌డేట్ లేదా కేంద్రం స్థానం చెప్పండి."
    if language == "ml":
        return "ആധാർ സഹായത്തിന്: പേര്/DOB തിരുത്തൽ, വിലാസം അപ്‌ഡേറ്റ്, മൊബൈൽ അപ്‌ഡേറ്റ്, അല്ലെങ്കിൽ കേന്ദ്ര സ്ഥലം പറയൂ."
    if language == "kn":
        return "ಆಧಾರ್ ಸಹಾಯಕ್ಕೆ: ಹೆಸರು/DOB ತಿದ್ದುಪಡಿ, ವಿಳಾಸ ಅಪ್‌ಡೇಟ್, ಮೊಬೈಲ್ ಅಪ್‌ಡೇಟ್ ಅಥವಾ ಕೇಂದ್ರ ಸ್ಥಳ ಹೇಳಿ."
    if language == "mr":
        return "आधार मदतीसाठी: नाव/DOB दुरुस्ती, पत्ता अपडेट, मोबाइल अपडेट किंवा केंद्र स्थान सांगा."
    if language == "bn":
        return "আধার সহায়তার জন্য: নাম/DOB সংশোধন, ঠিকানা আপডেট, মোবাইল আপডেট বা কেন্দ্রের অবস্থান বলুন।"
    return (
        "For Aadhaar help, tell me what you need: "
        "name/DOB correction, address update, mobile update, or center location."
    )


def _escalation_reply(language, agent_name=None):
    suffix = f": {agent_name}" if agent_name else ""
    if language == "ta":
        return f"உங்கள் கோரிக்கை மனித உதவிக்கு அனுப்பப்பட்டுள்ளது{suffix}."
    if language == "hi":
        return f"आपका अनुरोध मानव सहायता को भेज दिया गया है{suffix}."
    if language == "te":
        return f"మీ అభ్యర్థన మానవ సహాయానికి పంపబడింది{suffix}."
    if language == "ml":
        return f"നിങ്ങളുടെ അഭ്യർത്ഥന മനുഷ്യ സഹായത്തിലേക്ക് അയച്ചു{suffix}."
    if language == "kn":
        return f"ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಮಾನವ ಸಹಾಯಕ್ಕೆ ಕಳುಹಿಸಲಾಗಿದೆ{suffix}."
    if language == "mr":
        return f"तुमची विनंती मानवी सहाय्यासाठी पाठवली आहे{suffix}."
    if language == "bn":
        return f"আপনার অনুরোধ মানব সহায়তায় পাঠানো হয়েছে{suffix}."
    return f"Your request is escalated to human support{suffix}."


def _clarify_reply(language, repeated=False):
    if repeated:
        if language == "ta":
            return "நீங்கள் இதே கேள்வியை மீண்டும் கேட்டுள்ளீர்கள். தீர்வில்லையெனில் 'agent' என்று টাইப் செய்யவும்."
        if language == "hi":
            return "आपने वही प्रश्न फिर से पूछा है। यदि समाधान न मिले, 'agent' टाइप करें।"
        if language == "te":
            return "మీరు అదే ప్రశ్న మళ్లీ అడిగారు. పరిష్కారం లేకుంటే 'agent' టైప్ చేయండి."
        if language == "ml":
            return "നിങ്ങള്‍ ഇതേ ചോദ്യം വീണ്ടും ചോദിച്ചു. പരിഹാരം കിട്ടാനില്ലെങ്കിൽ 'agent' ടൈപ്പ് ചെയ്യൂ."
        if language == "kn":
            return "ನೀವು ಅದೇ ಪ್ರಶ್ನೆಯನ್ನು ಮತ್ತೆ ಕೇಳಿದ್ದೀರಿ. ಪರಿಹಾರವಾಗದಿದ್ದರೆ 'agent' ಟೈಪ್ ಮಾಡಿ."
        if language == "mr":
            return "तुम्ही तोच प्रश्न पुन्हा विचारला आहे. समाधान न मिळाल्यास 'agent' टाइप करा."
        if language == "bn":
            return "আপনি একই প্রশ্ন আবার করেছেন। সমাধান না হলে 'agent' লিখুন।"
        return "You asked a similar query again. If unresolved, type 'agent' to connect human support."
    if language == "ta":
        return "சேவை, இடம் மற்றும் நீங்கள் தேவைப்படுவது என்ன என்பதைக் கூறுங்கள்."
    if language == "hi":
        return "सेवा, स्थान और आपकी जरूरत स्पष्ट बताइए ताकि मैं सही उत्तर दे सकूं।"
    if language == "te":
        return "సేవ, ప్రాంతం మరియు మీ అవసరాన్ని వివరంగా చెప్పండి."
    if language == "ml":
        return "സേവനം, സ്ഥലം, നിങ്ങൾക്ക് വേണ്ടത് വിശദമായി പറയൂ."
    if language == "kn":
        return "ಸೇವೆ, ಸ್ಥಳ ಮತ್ತು ನಿಮ್ಮ ಅಗತ್ಯವನ್ನು ವಿವರವಾಗಿ ಹೇಳಿ."
    if language == "mr":
        return "सेवा, स्थान आणि तुमची गरज स्पष्टपणे सांगा."
    if language == "bn":
        return "সেবা, অবস্থান এবং আপনার প্রয়োজন স্পষ্ট করে বলুন।"
    return "Share service, location, and what exactly you need so I can give a direct answer."


def _next_step_prompt(service, language):
    if service:
        if language == "ta":
            return f"{service.name} தொடர்பாக அடுத்தது: ஆவணங்கள், அலுவலக நேரம், அருகிலுள்ள அலுவலகம், அல்லது புகார் நிலை?"
        if language == "hi":
            return f"{service.name} के लिए अगला क्या चाहिए: दस्तावेज़, कार्यालय समय, नजदीकी कार्यालय, या शिकायत स्थिति?"
        if language == "te":
            return f"{service.name} కి తదుపరి ఏమి కావాలి: పత్రాలు, కార్యాలయ సమయాలు, సమీప కార్యాలయం, లేదా ఫిర్యాదు స్థితి?"
        if language == "ml":
            return f"{service.name} ന് അടുത്തതായി: രേഖകൾ, ഓഫീസ് സമയം, സമീപ ഓഫീസ്, അല്ലെങ്കിൽ പരാതി നില?"
        if language == "kn":
            return f"{service.name}ಗೆ ಮುಂದೇನು ಬೇಕು: ದಾಖಲೆಗಳು, ಕಚೇರಿ ಸಮಯ, ಹತ್ತಿರದ ಕಚೇರಿ, ಅಥವಾ ದೂರು ಸ್ಥಿತಿ?"
        if language == "mr":
            return f"{service.name} साठी पुढे काय हवे: कागदपत्रे, कार्यालयीन वेळा, जवळचे कार्यालय, की तक्रार स्थिती?"
        if language == "bn":
            return f"{service.name} এর জন্য পরের ধাপ কী: নথি, অফিস সময়, কাছাকাছি অফিস, নাকি অভিযোগের অবস্থা?"
        return f"What next for {service.name}: documents, office timings, nearest office, or complaint status?"
    if language == "ta":
        return "அடுத்ததாக என்ன வேண்டும்: ஆவணங்கள், அலுவலக நேரம், அருகிலுள்ள அலுவலகம், பணம்/பில் உதவி, அல்லது புகார் நிலை?"
    if language == "hi":
        return "अगला क्या चाहिए: दस्तावेज़, कार्यालय समय, नजदीकी कार्यालय, भुगतान/बिल मदद, या शिकायत स्थिति?"
    if language == "te":
        return "తదుపరి ఏమి కావాలి: పత్రాలు, కార్యాలయ సమయాలు, సమీప కార్యాలయం, బిల్/పేమెంట్ సహాయం, లేదా ఫిర్యాదు స్థితి?"
    if language == "ml":
        return "അടുത്തത് എന്ത് വേണം: രേഖകൾ, ഓഫീസ് സമയം, സമീപ ഓഫീസ്, ബിൽ/പേയ്മെന്റ് സഹായം, അല്ലെങ്കിൽ പരാതി നില?"
    if language == "kn":
        return "ಮುಂದೇನು ಬೇಕು: ದಾಖಲೆಗಳು, ಕಚೇರಿ ಸಮಯ, ಹತ್ತಿರದ ಕಚೇರಿ, ಬಿಲ್/ಪಾವತಿ ಸಹాయం, ಅಥವಾ ದೂರು ಸ್ಥಿತಿ?"
    if language == "mr":
        return "पुढे काय हवे: कागदपत्रे, कार्यालयीन वेळा, जवळचे कार्यालय, बिल/पेमेंट मदत, किंवा तक्रार स्थिती?"
    if language == "bn":
        return "এরপর কী চান: নথি, অফিস সময়, কাছাকাছি অফিস, বিল/পেমেন্ট সহায়তা, বা অভিযোগের অবস্থা?"
    return "What would you like next: documents, office timings, nearest office, bill/payment help, or complaint status?"


def _assistance_followup(language):
    if language == "ta":
        return "மேலும் உதவி வேண்டுமா?"
    if language == "hi":
        return "क्या आपको और सहायता चाहिए?"
    if language == "te":
        return "ఇంకా సహాయం కావాలా?"
    if language == "ml":
        return "കൂടുതൽ സഹായം വേണോ?"
    if language == "kn":
        return "ಇನ್ನೂ ಸಹಾಯ ಬೇಕೆ?"
    if language == "mr":
        return "आणखी मदत हवी आहे का?"
    if language == "bn":
        return "আরও সাহায্য দরকার?"
    return "Need any more assistance?"


def _complaint_status_reply(session, language):
    complaint = getattr(session, "complaint", None)
    if complaint is None:
        if language == "ta":
            return "இந்த அமர்விற்கு புகார் இல்லை. தேவையெனில் 'agent' என்று টাইப் செய்து உயர்த்தலாம்."
        if language == "hi":
            return "इस सत्र के लिए कोई शिकायत नहीं मिली। जरूरत हो तो 'agent' टाइप करें।"
        if language == "te":
            return "ఈ సెషన్‌కు ఫిర్యాదు లేదు. అవసరమైతే 'agent' టైప్ చేయండి."
        if language == "ml":
            return "ഈ സെഷനിൽ പരാതിയില്ല. ആവശ്യമെങ്കിൽ 'agent' ടൈപ്പ് ചെയ്യൂ."
        if language == "kn":
            return "ಈ ಸೆಷನ್‌ಗೆ ದೂರು ಇಲ್ಲ. ಅಗತ್ಯವಿದ್ದರೆ 'agent' ಟೈಪ್ ಮಾಡಿ."
        if language == "mr":
            return "या सत्रासाठी तक्रार नाही. गरज असल्यास 'agent' टाइप करा."
        if language == "bn":
            return "এই সেশনের জন্য কোনো অভিযোগ নেই। প্রয়োজন হলে 'agent' লিখুন।"
        return "No complaint found for this session. If needed, type 'agent' to escalate and create one."

    status_map = {
        "open": "Filed",
        "in_progress": "Review",
        "resolved": "Closed",
        "closed": "Closed",
    }
    current_step = status_map.get((complaint.status or "").lower(), "Filed")
    steps_line = "Steps: Filed, Assigned, Review, Work, Closed"
    if language == "ta":
        steps_line = "படிகள்: Filed, Assigned, Review, Work, Closed"
    elif language == "hi":
        steps_line = "चरण: Filed, Assigned, Review, Work, Closed"
    elif language == "te":
        steps_line = "దశలు: Filed, Assigned, Review, Work, Closed"
    elif language == "ml":
        steps_line = "ഘട്ടങ്ങൾ: Filed, Assigned, Review, Work, Closed"
    elif language == "kn":
        steps_line = "ಹಂತಗಳು: Filed, Assigned, Review, Work, Closed"
    elif language == "mr":
        steps_line = "टप्पे: Filed, Assigned, Review, Work, Closed"
    elif language == "bn":
        steps_line = "ধাপ: Filed, Assigned, Review, Work, Closed"
    if language == "ta":
        return (
            "புகார் நிலை:\n"
            f"ID: {complaint.tracking_id}\n"
            f"நிலை: {complaint.status}\n"
            f"{steps_line}\n"
            f"தற்போதைய நிலை: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "hi":
        return (
            "शिकायत स्थिति:\n"
            f"ID: {complaint.tracking_id}\n"
            f"स्थिति: {complaint.status}\n"
            f"{steps_line}\n"
            f"वर्तमान चरण: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "te":
        return (
            "ఫిర్యాదు స్థితి:\n"
            f"ID: {complaint.tracking_id}\n"
            f"స్థితి: {complaint.status}\n"
            f"{steps_line}\n"
            f"ప్రస్తుత దశ: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "ml":
        return (
            "പരാതി നില:\n"
            f"ID: {complaint.tracking_id}\n"
            f"സ്ഥിതി: {complaint.status}\n"
            f"{steps_line}\n"
            f"ഇപ്പോൾഘട്ടം: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "kn":
        return (
            "ದೂರು ಸ್ಥಿತಿ:\n"
            f"ID: {complaint.tracking_id}\n"
            f"ಸ್ಥಿತಿ: {complaint.status}\n"
            f"{steps_line}\n"
            f"ಪ್ರಸ್ತುತ ಹಂತ: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "mr":
        return (
            "तक्रार स्थिती:\n"
            f"ID: {complaint.tracking_id}\n"
            f"स्थिती: {complaint.status}\n"
            f"{steps_line}\n"
            f"सध्याचा टप्पा: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    if language == "bn":
        return (
            "অভিযোগের অবস্থা:\n"
            f"ID: {complaint.tracking_id}\n"
            f"স্থিতি: {complaint.status}\n"
            f"{steps_line}\n"
            f"বর্তমান ধাপ: {current_step}\n"
            f"{_assistance_followup(language)}"
        )
    return (
        "Complaint Status:\n"
        f"ID: {complaint.tracking_id}\n"
        f"Status: {complaint.status}\n"
        f"{steps_line}\n"
        f"Current Step: {current_step}\n"
        f"{_assistance_followup(language)}"
    )


def _maps_nearby_link(service, content):
    raw_text = content or ""
    normalized = _normalize_text(raw_text)
    location = ""
    match = LOCATION_SPLIT_PATTERN.search(normalized)
    if match:
        location = (match.group(1) or "").strip()

    location = location.replace("near me", "").strip()
    location = re.sub(r"\s+", " ", location)

    lat_lon_match = LAT_LON_PATTERN.search(raw_text) or LAT_LON_PATTERN.search(raw_text.lower())
    if lat_lon_match:
        lat = lat_lon_match.group(1)
        lon = lat_lon_match.group(2)
        query = f"{service.name} near {lat},{lon}"
    else:
        query = f"{service.name} near me" if not location else f"{service.name} near {location}"
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def _dedupe_assistant_reply(session, ai_text, language):
    last_ai = (
        Message.objects.filter(session=session, sender_role="assistant")
        .order_by("-created_at")
        .values_list("content", flat=True)
        .first()
    )
    if last_ai and _normalize_text(last_ai) == _normalize_text(ai_text):
        n_assistant = Message.objects.filter(session=session, sender_role="assistant").count()
        return _fallback_reply(language, variant=n_assistant + 1)
    return ai_text


def process_user_message(session, user, content):
    language = detect_language(content, fallback=session.language_preference)
    role = "citizen"
    if getattr(user, "role", "") == "ADMIN" or user.is_staff or user.is_superuser:
        role = "admin"

    previous_user_content = (
        Message.objects.filter(session=session, sender_role="citizen")
        .order_by("-created_at")
        .values_list("content", flat=True)
        .first()
    )

    user_msg = Message.objects.create(
        session=session,
        sender=user,
        sender_role=role,
        content=content,
        language=language,
        is_from_ai=False,
    )

    ai_msg = None
    escalated = False

    if role == "citizen":
        if _is_greeting_or_help(content):
            ai_text = _dedupe_assistant_reply(session, _greeting_reply(language), language)
            ai_msg = Message.objects.create(
                session=session,
                sender=None,
                sender_role="assistant",
                content=ai_text,
                language=language,
                is_from_ai=True,
            )
            session.last_message_at = user_msg.created_at
            if session.language_preference != language:
                session.language_preference = language
                session.save(update_fields=["last_message_at", "language_preference", "updated_at"])
            else:
                session.save(update_fields=["last_message_at", "updated_at"])
            return user_msg, ai_msg, escalated

        if _is_thanks(content):
            ai_text = _dedupe_assistant_reply(session, _thanks_reply(language), language)
            ai_msg = Message.objects.create(
                session=session,
                sender=None,
                sender_role="assistant",
                content=ai_text,
                language=language,
                is_from_ai=True,
            )
            session.last_message_at = user_msg.created_at
            if session.language_preference != language:
                session.language_preference = language
                session.save(update_fields=["last_message_at", "language_preference", "updated_at"])
            else:
                session.save(update_fields=["last_message_at", "updated_at"])
            return user_msg, ai_msg, escalated

        inferred_service = _infer_service(content)
        if inferred_service and session.service_id != inferred_service.id:
            session.service = inferred_service
            session.save(update_fields=["service", "updated_at"])

        repeated_user_query = previous_user_content is not None and _normalize_text(previous_user_content) == _normalize_text(content)

        if needs_escalation(content):
            escalated = True
            session.status = "escalated"
            if not session.assigned_agent:
                session.assigned_agent = _pick_agent()
            session.save(update_fields=["status", "assigned_agent", "updated_at"])
            lat, lon, location_text = _extract_user_location(content)
            complaint = create_complaint_from_session(
                session=session,
                created_by=user,
                title=f"{session.service.name if session.service else 'Civic'} support escalation",
                description=content,
                latitude=lat,
                longitude=lon,
                location_address=location_text or "",
            )
            ai_text = (
                f"{_escalation_reply(language, getattr(session.assigned_agent, 'username', None))}\n"
                f"Complaint ID: {complaint.tracking_id}"
            )
            _create_notification(
                session.user,
                "Agent request sent",
                f"Your session {session.complaint_tracking_id} has been escalated to support. Complaint ID: {complaint.tracking_id}",
                "/civic/profile/",
            )
            if session.assigned_agent:
                _create_notification(
                    session.assigned_agent,
                    "Citizen requested agent support",
                    f"Session {session.complaint_tracking_id} needs your response. Complaint ID: {complaint.tracking_id}",
                    "/admin/civic/complaint/",
                )
        elif repeated_user_query:
            ai_text = _clarify_reply(language, repeated=True)
        else:
            intent = _detect_intent(content)
            aadhaar_reply = _aadhaar_specific_reply(content, language)
            if aadhaar_reply:
                ai_text = f"{aadhaar_reply}\n{_assistance_followup(language)}"
            elif session.service and intent == "documents":
                ai_text = f"{_format_documents_reply(session.service, language)}\n{_next_step_prompt(session.service, language)}"
            elif session.service and intent in ("office", "timings"):
                nearby_map_link = _maps_nearby_link(session.service, content)
                office_reply = _format_office_reply(session.service, language, content)
                if "nearby map search:" in office_reply.lower():
                    ai_text = f"{office_reply}\n{_assistance_followup(language)}"
                else:
                    if language == "ta":
                        map_label = "அருகிலுள்ள மேப் இணைப்பு"
                    elif language == "hi":
                        map_label = "नजदीकी मैप लिंक"
                    elif language == "te":
                        map_label = "సమీప మ్యాప్ లింక్"
                    elif language == "ml":
                        map_label = "സമീപ മാപ്പ് ലിങ്ക്"
                    elif language == "kn":
                        map_label = "ಹತ್ತಿರದ ಮ್ಯಾಪ್ ಲಿಂಕ್"
                    elif language == "mr":
                        map_label = "जवळचा मॅप लिंक"
                    elif language == "bn":
                        map_label = "কাছাকাছি ম্যাপ লিংক"
                    else:
                        map_label = "Nearby map link"
                    ai_text = (
                        f"{office_reply}\n"
                        f"{map_label}: {nearby_map_link}\n"
                        f"{_assistance_followup(language)}"
                    )
            elif intent == "tracking":
                ai_text = _complaint_status_reply(session, language)
            else:
                direct_text = _service_specific_reply(session.service, intent, content, language)
                if direct_text:
                    kb_text = direct_text
                else:
                    kb_text = find_kb_answer(session.service, content, language, session=session)
                if kb_text:
                    ai_text = f"{kb_text}\n{_next_step_prompt(session.service, language)}"
                else:
                    n_assistant = Message.objects.filter(session=session, sender_role="assistant").count()
                    if session.service and intent in ("payment", "new_connection", "tracking"):
                        if language == "ta":
                            ai_text = (
                                f"{session.service.name} தொடர்பாக கட்டணம், புதிய இணைப்பு, மற்றும் கண்காணிப்பு வழிமுறைகள் தர முடியும். "
                                "உங்கள் நகரம் மற்றும் குறிப்பு/சேவை எண்ணை பகிருங்கள்.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "hi":
                            ai_text = (
                                f"{session.service.name} के लिए भुगतान, नया कनेक्शन और ट्रैकिंग में मदद कर सकता हूँ। "
                                "अपना शहर और संदर्भ/सेवा नंबर बताइए।\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "te":
                            ai_text = (
                                f"{session.service.name} కోసం పేమెంట్, కొత్త కనెక్షన్, ట్రాకింగ్ సహాయం చేయగలను. "
                                "మీ నగరం మరియు రిఫరెన్స్/సేవ నంబర్ చెప్పండి.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "ml":
                            ai_text = (
                                f"{session.service.name} സംബന്ധിച്ച് പേയ്‌മെന്റ്, പുതിയ കണക്ഷൻ, ട്രാക്കിംഗ് സഹായം നൽകാം. "
                                "നിങ്ങളുടെ നഗരംയും റഫറൻസ്/സർവീസ് നമ്പറും പങ്കിടൂ.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "kn":
                            ai_text = (
                                f"{session.service.name}ಗಾಗಿ ಪಾವತಿ, ಹೊಸ ಸಂಪರ್ಕ, ಟ್ರ್ಯಾಕಿಂಗ್ ಸಹಾಯ ನೀಡಬಹುದು. "
                                "ನಿಮ್ಮ ನಗರ ಮತ್ತು ರೆಫರೆನ್ಸ್/ಸೇವಾ ಸಂಖ್ಯೆಯನ್ನು ತಿಳಿಸಿ.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "mr":
                            ai_text = (
                                f"{session.service.name} साठी पेमेंट, नवीन कनेक्शन आणि ट्रॅकिंगची मदत करू शकतो. "
                                "तुमचे शहर आणि रेफरन्स/सेवा क्रमांक सांगा.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        elif language == "bn":
                            ai_text = (
                                f"{session.service.name} এর জন্য পেমেন্ট, নতুন সংযোগ ও ট্র্যাকিং সহায়তা দিতে পারি। "
                                "আপনার শহর ও রেফারেন্স/সেবা নম্বর দিন।\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                        else:
                            ai_text = (
                                f"For {session.service.name}, I can guide payment, new connection, and tracking steps. "
                                f"Please share your city and reference/service number if available.\n"
                                f"{_next_step_prompt(session.service, language)}"
                            )
                    else:
                        ai_text = _fallback_reply(language, variant=n_assistant)

        ai_text = _dedupe_assistant_reply(session, ai_text, language)
        ai_msg = Message.objects.create(
            session=session,
            sender=None,
            sender_role="assistant",
            content=ai_text,
            language=language,
            is_from_ai=True,
        )

    if session.service:
        stat, _ = ServiceUsageStat.objects.get_or_create(service=session.service, date=date.today())
        stat.total_queries += 1
        if escalated:
            stat.escalated_queries += 1
        stat.save(update_fields=["total_queries", "escalated_queries"])

    session.last_message_at = user_msg.created_at
    if session.language_preference != language:
        session.language_preference = language
        session.save(update_fields=["last_message_at", "language_preference", "updated_at"])
    else:
        session.save(update_fields=["last_message_at", "updated_at"])

    return user_msg, ai_msg, escalated


def create_complaint_from_session(session, created_by, title, description, latitude=None, longitude=None, location_address=""):
    if hasattr(session, "complaint"):
        return session.complaint

    complaint = Complaint.objects.create(
        session=session,
        service=session.service,
        created_by=created_by,
        assigned_to=session.assigned_agent,
        title=title,
        description=description,
        tracking_id=_next_tracking_id(Complaint, "tracking_id", "CMP"),
        latitude=latitude,
        longitude=longitude,
        location_address=location_address or "",
    )

    if session.service:
        stat, _ = ServiceUsageStat.objects.get_or_create(service=session.service, date=date.today())
        stat.complaints_raised += 1
        stat.save(update_fields=["complaints_raised"])

    return complaint
