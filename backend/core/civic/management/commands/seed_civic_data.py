from django.core.management.base import BaseCommand

from civic.models import DocumentsRequired, KnowledgeBase, Office, Service


SERVICES = [
    {"code": "post-office", "name": "Post Office", "description": "Postal, savings, and Aadhaar-linked services."},
    {"code": "electricity-board", "name": "Electricity Board", "description": "Bill payment, new connection, and complaint support."},
    {"code": "bank-services", "name": "Bank Services", "description": "Account, KYC, loans, and ATM support."},
    {"code": "government-offices", "name": "Government Offices", "description": "Ration card, certificates, land and pension services."},
]


OFFICES = {
    "post-office": [
        {
            "name": "Chennai GPO",
            "address": "No. 1 Rajaji Salai, Parrys",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600001",
            "contact_phone": "044-2523-1234",
            "timings": "Mon-Sat 10:00 AM - 5:00 PM",
            "google_map_link": "https://maps.google.com/?q=Chennai+GPO",
        },
        {
            "name": "Madurai Head Post Office",
            "address": "Town Hall Road",
            "city": "Madurai",
            "state": "Tamil Nadu",
            "pincode": "625001",
            "contact_phone": "0452-234-5678",
            "timings": "Mon-Sat 10:00 AM - 5:00 PM",
            "google_map_link": "https://maps.google.com/?q=Madurai+Head+Post+Office",
        },
    ],
    "electricity-board": [
        {
            "name": "TNEB Anna Nagar Section Office",
            "address": "2nd Avenue, Anna Nagar",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600040",
            "contact_phone": "1912",
            "timings": "Mon-Fri 9:30 AM - 5:30 PM",
            "google_map_link": "https://maps.google.com/?q=TNEB+Anna+Nagar",
        },
        {
            "name": "TNEB Coimbatore North Office",
            "address": "Mettupalayam Road",
            "city": "Coimbatore",
            "state": "Tamil Nadu",
            "pincode": "641002",
            "contact_phone": "1912",
            "timings": "Mon-Fri 9:30 AM - 5:30 PM",
            "google_map_link": "https://maps.google.com/?q=TNEB+Coimbatore",
        },
    ],
    "bank-services": [
        {
            "name": "State Bank Main Branch",
            "address": "Mount Road",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600002",
            "contact_phone": "1800-11-2211",
            "timings": "Mon-Fri 10:00 AM - 4:00 PM",
            "google_map_link": "https://maps.google.com/?q=SBI+Main+Branch+Chennai",
        },
        {
            "name": "Indian Bank Trichy Branch",
            "address": "Cantonment",
            "city": "Tiruchirappalli",
            "state": "Tamil Nadu",
            "pincode": "620001",
            "contact_phone": "1800-425-00-000",
            "timings": "Mon-Fri 10:00 AM - 4:00 PM",
            "google_map_link": "https://maps.google.com/?q=Indian+Bank+Trichy",
        },
    ],
    "government-offices": [
        {
            "name": "Taluk Office - Egmore",
            "address": "Near Commissioner Office, Egmore",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600008",
            "contact_phone": "044-2819-0000",
            "timings": "Mon-Fri 10:00 AM - 5:45 PM",
            "google_map_link": "https://maps.google.com/?q=Taluk+Office+Egmore",
        },
        {
            "name": "e-Sevai Centre - Salem",
            "address": "Collectorate Campus",
            "city": "Salem",
            "state": "Tamil Nadu",
            "pincode": "636001",
            "contact_phone": "1800-425-1333",
            "timings": "Mon-Sat 9:00 AM - 6:00 PM",
            "google_map_link": "https://maps.google.com/?q=eSevai+Centre+Salem",
        },
    ],
}


DOCUMENTS = [
    {
        "service": "post-office",
        "title": "Aadhaar Address Update - Documents",
        "details": "Aadhaar copy, valid ID proof, address proof, and filled update request form.",
        "language": "en",
    },
    {
        "service": "post-office",
        "title": "ஆதார் முகவரி புதுப்பிப்பு - ஆவணங்கள்",
        "details": "ஆதார் நகல், அடையாள அட்டை, முகவரி சான்று மற்றும் புதுப்பிப்பு விண்ணப்பம்.",
        "language": "ta",
    },
    {
        "service": "electricity-board",
        "title": "Name Change in EB - Documents",
        "details": "Latest EB bill, ID proof, address proof, ownership/rental proof, and request letter.",
        "language": "en",
    },
    {
        "service": "electricity-board",
        "title": "EB பெயர் மாற்றம் - ஆவணங்கள்",
        "details": "சமீபத்திய EB பில், அடையாள சான்று, முகவரி சான்று, சொத்து/வாடகை சான்று, கோரிக்கை கடிதம்.",
        "language": "ta",
    },
    {
        "service": "bank-services",
        "title": "Savings Account Opening - Documents",
        "details": "PAN or Form 60, Aadhaar, passport-size photo, and mobile number.",
        "language": "en",
    },
    {
        "service": "bank-services",
        "title": "சேமிப்பு கணக்கு திறப்பு - ஆவணங்கள்",
        "details": "PAN அல்லது Form 60, ஆதார், பாஸ்போர்ட் அளவு புகைப்படம், மொபைல் எண்.",
        "language": "ta",
    },
    {
        "service": "government-offices",
        "title": "Ration Card Application - Documents",
        "details": "Family photo, Aadhaar for family members, address proof, and income details.",
        "language": "en",
    },
    {
        "service": "government-offices",
        "title": "ரேஷன் கார்டு விண்ணப்பம் - ஆவணங்கள்",
        "details": "குடும்பப் புகைப்படம், குடும்ப உறுப்பினர்களின் ஆதார், முகவரி சான்று, வருமான விவரம்.",
        "language": "ta",
    },
]


KB_ENTRIES = [
    {
        "service": "post-office",
        "language": "en",
        "question": "What are post office timings?",
        "answer": "Most post offices work from 10:00 AM to 5:00 PM (Mon-Sat). For parcel counters, timings may vary by branch.",
        "keywords": "post office,timings,working hours,parcel,speed post",
        "priority": 10,
    },
    {
        "service": "post-office",
        "language": "ta",
        "question": "தபால் அலுவலக நேரம் என்ன?",
        "answer": "பொதுவாக தபால் அலுவலகம் திங்கள் முதல் சனி வரை காலை 10:00 முதல் மாலை 5:00 வரை செயல்படும்.",
        "keywords": "தபால்,நேரம்,வேலை நேரம்,பார்சல்",
        "priority": 10,
    },
    {
        "service": "electricity-board",
        "language": "en",
        "question": "How can I pay EB bill?",
        "answer": "You can pay via EB online portal/app, e-Sevai center, or section office counter. Keep service number ready.",
        "keywords": "eb,bill,payment,service number,current bill",
        "priority": 10,
    },
    {
        "service": "electricity-board",
        "language": "ta",
        "question": "EB பில் எப்படி செலுத்துவது?",
        "answer": "EB portal/app, e-Sevai மையம், அல்லது அலுவலக கவுண்டரில் கட்டலாம். சேவை எண் தயாராக வைத்திருக்கவும்.",
        "keywords": "eb,பில்,கட்டணம்,சேவை எண்",
        "priority": 10,
    },
    {
        "service": "bank-services",
        "language": "en",
        "question": "How to update KYC in bank?",
        "answer": "Visit your branch with ID and address proof, fill KYC update form, and submit self-attested copies.",
        "keywords": "bank,kyc,update,id proof,address proof",
        "priority": 10,
    },
    {
        "service": "bank-services",
        "language": "ta",
        "question": "வங்கி KYC எப்படி புதுப்பிப்பது?",
        "answer": "அருகிலுள்ள கிளைக்கு அடையாள சான்று மற்றும் முகவரி சான்று கொண்டு சென்று KYC படிவத்தை சமர்ப்பிக்கவும்.",
        "keywords": "வங்கி,kyc,புதுப்பிப்பு,அடையாள சான்று",
        "priority": 10,
    },
    {
        "service": "government-offices",
        "language": "en",
        "question": "How to apply ration card?",
        "answer": "Apply through Tamil Nadu e-Sevai portal/center with family and address documents. Track via application reference ID.",
        "keywords": "ration card,apply,documents,esevai,reference",
        "priority": 10,
    },
    {
        "service": "government-offices",
        "language": "ta",
        "question": "ரேஷன் கார்டுக்கு எப்படி விண்ணப்பிப்பது?",
        "answer": "தமிழ்நாடு e-Sevai portal/மையம் மூலம் குடும்ப மற்றும் முகவரி ஆவணங்களுடன் விண்ணப்பிக்கலாம்.",
        "keywords": "ரேஷன்,விண்ணப்பம்,ஆவணங்கள்,esevai,கண்காணிப்பு",
        "priority": 10,
    },
]


class Command(BaseCommand):
    help = "Seed starter civic data (services, offices, documents, and knowledge base) for chatbot responses."

    def handle(self, *args, **options):
        service_map = {}

        for row in SERVICES:
            service, _ = Service.objects.update_or_create(
                code=row["code"],
                defaults={
                    "name": row["name"],
                    "description": row["description"],
                    "is_active": True,
                },
            )
            service_map[row["code"]] = service

        for code, office_rows in OFFICES.items():
            service = service_map[code]
            for office in office_rows:
                Office.objects.update_or_create(
                    service=service,
                    name=office["name"],
                    city=office["city"],
                    defaults={
                        "address": office["address"],
                        "state": office["state"],
                        "pincode": office["pincode"],
                        "contact_phone": office["contact_phone"],
                        "timings": office["timings"],
                        "google_map_link": office["google_map_link"],
                        "is_active": True,
                    },
                )

        for doc in DOCUMENTS:
            service = service_map[doc["service"]]
            DocumentsRequired.objects.update_or_create(
                service=service,
                title=doc["title"],
                language=doc["language"],
                defaults={
                    "details": doc["details"],
                    "is_active": True,
                },
            )

        for kb in KB_ENTRIES:
            service = service_map[kb["service"]]
            KnowledgeBase.objects.update_or_create(
                service=service,
                language=kb["language"],
                question=kb["question"],
                defaults={
                    "answer": kb["answer"],
                    "keywords": kb["keywords"],
                    "priority": kb["priority"],
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Civic starter data seeded successfully."))
