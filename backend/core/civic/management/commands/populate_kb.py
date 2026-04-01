import ast
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from civic.models import KnowledgeBase, Service


class Command(BaseCommand):
    help = "Populate KnowledgeBase from a prompt file containing entries = [{...}]"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=r"C:\Users\ELITEBOOK\Downloads\knowledge-base-populate-prompt.txt",
            help="Path to source prompt txt file",
        )

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    def _extract_entries_literal(self, text: str) -> str:
        match = re.search(r"entries\s*=\s*\[", text)
        if not match:
            raise CommandError("Could not find 'entries = [' in source file")

        start = match.end() - 1
        depth = 0
        in_str = False
        escape = False
        quote_char = ""

        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote_char:
                    in_str = False
            else:
                if ch in ("'", '"'):
                    in_str = True
                    quote_char = ch
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]

        raise CommandError("Could not parse entries list from source file")

    def _keywords_from_question(self, question: str, category: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9\s]", " ", question.lower())
        words = [w for w in base.split() if len(w) > 2]
        cat_words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", (category or "").lower()).split() if len(w) > 2]
        merged = []
        for w in (words + cat_words):
            if w not in merged:
                merged.append(w)
        return ", ".join(merged[:20])

    def _map_service(self, category: str):
        c = (category or "").lower()
        all_services = list(Service.objects.filter(is_active=True))
        if not all_services:
            return None

        def find_any(tokens):
            for s in all_services:
                blob = f"{(s.name or '').lower()} {(s.code or '').lower()}"
                if any(t in blob for t in tokens):
                    return s
            return None

        if any(t in c for t in ["electric", "power", "eb"]):
            return find_any(["electric", "eb", "power"])
        if any(t in c for t in ["bank", "finance", "loan"]):
            return find_any(["bank", "finance", "loan"])
        if any(t in c for t in ["post", "postal"]):
            return find_any(["post", "postal"])
        if any(t in c for t in ["gov", "revenue", "certificate", "land", "water", "transport", "police", "housing", "grievance", "health", "education"]):
            return find_any(["government", "gov", "revenue", "certificate"])
        return None

    def handle(self, *args, **kwargs):
        source = Path(kwargs["source"]) 
        if not source.exists():
            raise CommandError(f"Source file not found: {source}")

        text = self._read_text(source)
        literal = self._extract_entries_literal(text)

        try:
            entries = ast.literal_eval(literal)
        except Exception as exc:
            raise CommandError(f"Failed to parse entries literal: {exc}")

        if not isinstance(entries, list):
            raise CommandError("Parsed entries is not a list")

        if "EXTRA_ENTRIES" in globals():
            entries.extend(EXTRA_ENTRIES)

        created = 0
        updated = 0
        skipped = 0

        for entry in entries:
            question = (entry.get("question") or "").strip()
            answer = (entry.get("answer") or "").strip()
            language = (entry.get("language") or "en").strip().lower()
            category = (entry.get("category") or "").strip()

            if not question or not answer:
                skipped += 1
                continue

            if language not in {"en", "ta", "hi", "te", "ml", "kn", "mr", "bn"}:
                language = "en"

            keywords = self._keywords_from_question(question, category)
            service = self._map_service(category)

            obj, was_created = KnowledgeBase.objects.get_or_create(
                question=question,
                language=language,
                defaults={
                    "answer": answer,
                    "keywords": keywords,
                    "service": service,
                    "priority": 100,
                    "is_active": True,
                },
            )

            if was_created:
                created += 1
            else:
                changed = False
                if obj.answer != answer:
                    obj.answer = answer
                    changed = True
                if keywords and obj.keywords != keywords:
                    obj.keywords = keywords
                    changed = True
                if not obj.service and service:
                    obj.service = service
                    changed = True
                if not obj.is_active:
                    obj.is_active = True
                    changed = True
                if changed:
                    obj.save(update_fields=["answer", "keywords", "service", "is_active"])
                    updated += 1
                else:
                    skipped += 1

        total = KnowledgeBase.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}"))
        self.stdout.write(self.style.SUCCESS(f"Total KnowledgeBase entries: {total}"))

# Extra multilingual KB entries
EXTRA_ENTRIES = [
    # HINDI (hi)
    { 'question': 'जमीन का खसरा खतौनी कैसे निकालें?', 'answer': 'जमीन का खसरा खतौनी अपने राज्य के भूमि रिकॉर्ड पोर्टल से ऑनलाइन निकाल सकते हैं। उत्तर प्रदेश में upbhulekh.gov.in, मध्यप्रदेश में mpbhulekh.gov.in पर जाएं। जिला, तहसील और गांव का नाम चुनें। खाता नंबर या खसरा नंबर डालें। नकल डाउनलोड करें।', 'language': 'hi', 'category': 'Revenue & Land' },
    { 'question': 'जमीन रजिस्ट्री के लिए क्या दस्तावेज चाहिए?', 'answer': 'जमीन रजिस्ट्री के लिए: विक्रय पत्र, खसरा खतौनी, आधार कार्ड, PAN कार्ड, पासपोर्ट फोटो और संपत्ति कर रसीद चाहिए। स्टाम्प शुल्क और पंजीकरण शुल्क का भुगतान करना होगा। नजदीकी सब रजिस्ट्रार कार्यालय में जाएं।', 'language': 'hi', 'category': 'Revenue & Land' },
    { 'question': 'नया पानी का कनेक्शन कैसे लें?', 'answer': 'नया जल कनेक्शन के लिए नगर पालिका या जल बोर्ड कार्यालय में आवेदन करें। आवश्यक दस्तावेज: आवेदन पत्र, आधार कार्ड, संपत्ति कर रसीद, पते का प्रमाण। शुल्क जमा करें। कनेक्शन 15-30 दिनों में मिलता है।', 'language': 'hi', 'category': 'Water Supply' },
    { 'question': 'पानी पाइप लीकेज की शिकायत कैसे करें?', 'answer': 'पानी पाइप लीकेज की शिकायत नगर पालिका हेल्पलाइन पर करें। Fix My Street पोर्टल पर भी शिकायत दर्ज कर सकते हैं। राष्ट्रीय जल शिकायत हेल्पलाइन 1800-180-5678 पर कॉल करें।', 'language': 'hi', 'category': 'Water Supply' },
    { 'question': 'सरकारी अस्पताल में OPD में कैसे पंजीकरण करें?', 'answer': 'सरकारी अस्पताल में OPD पंजीकरण के लिए आधार कार्ड लेकर ओपीडी काउंटर पर जाएं। पंजीकरण निःशुल्क है। सुबह जल्दी जाएं क्योंकि टोकन सीमित होते हैं।', 'language': 'hi', 'category': 'Health' },
    { 'question': 'आयुष्मान भारत कार्ड कैसे बनवाएं?', 'answer': 'आयुष्मान भारत कार्ड के लिए नजदीकी कॉमन सर्विस सेंटर या सरकारी अस्पताल में जाएं। आधार कार्ड और राशन कार्ड लेकर जाएं। pmjay.gov.in पर पात्रता जांचें। यह योजना 5 लाख रुपये तक का स्वास्थ्य बीमा प्रदान करती है।', 'language': 'hi', 'category': 'Health' },
    { 'question': 'एम्बुलेंस कैसे बुलाएं?', 'answer': '108 डायल करके निःशुल्क सरकारी एम्बुलेंस बुला सकते हैं। यह सेवा 24 घंटे 7 दिन उपलब्ध है। आपातकालीन चिकित्सा, दुर्घटना और प्रसव मामलों के लिए उपलब्ध है।', 'language': 'hi', 'category': 'Health' },
    { 'question': 'विकलांगता प्रमाण पत्र कैसे बनवाएं?', 'answer': 'विकलांगता प्रमाण पत्र के लिए सरकारी अस्पताल में मेडिकल बोर्ड के सामने आवेदन करें। RPWD Act 2016 के तहत Form IV भरें। आधार कार्ड, चिकित्सा रिकॉर्ड और पासपोर्ट फोटो लेकर जाएं।', 'language': 'hi', 'category': 'Health' },
    { 'question': 'स्कूल से ट्रांसफर सर्टिफिकेट कैसे लें?', 'answer': 'ट्रांसफर सर्टिफिकेट के लिए स्कूल कार्यालय में 7-10 दिन पहले आवेदन करें। सभी बकाया फीस और लाइब्रेरी किताबें जमा करें। प्रधानाचार्य के हस्ताक्षर के बाद TC जारी होती है। यह निःशुल्क है।', 'language': 'hi', 'category': 'Education' },
    { 'question': 'सरकारी छात्रवृत्ति के लिए आवेदन कैसे करें?', 'answer': 'सरकारी छात्रवृत्ति के लिए scholarships.gov.in पर आवेदन करें। SC/ST, OBC, अल्पसंख्यक और मेरिट छात्रवृत्ति उपलब्ध हैं। आधार, आय प्रमाण और जाति प्रमाण पत्र आवश्यक है।', 'language': 'hi', 'category': 'Education' },
    { 'question': 'PM किसान का पैसा कैसे चेक करें?', 'answer': 'PM किसान भुगतान स्थिति pmkisan.gov.in पर Beneficiary Status में जाकर आधार नंबर, खाता नंबर या मोबाइल नंबर से चेक करें। पात्र किसानों को प्रतिवर्ष 6000 रुपये तीन किस्तों में मिलते हैं।', 'language': 'hi', 'category': 'Agriculture' },
    { 'question': 'फसल बीमा के लिए आवेदन कैसे करें?', 'answer': 'फसल बीमा (PMFBY) के लिए नजदीकी बैंक, कॉमन सर्विस सेंटर या pmfby.gov.in पर आवेदन करें। फसल सीजन की कट-ऑफ तारीख से पहले आवेदन करें। रबी के लिए 1.5% और खरीफ के लिए 2% प्रीमियम है।', 'language': 'hi', 'category': 'Agriculture' },
    { 'question': 'विधवा पेंशन के लिए आवेदन कैसे करें?', 'answer': 'विधवा पेंशन के लिए नगर पालिका या पंचायत कार्यालय में आवेदन करें। आवश्यक दस्तावेज: पति का मृत्यु प्रमाण पत्र, आधार, राशन कार्ड, बैंक पासबुक और आयु प्रमाण। BPL महिलाओं को 1000 रुपये प्रतिमाह मिलते हैं।', 'language': 'hi', 'category': 'Social Welfare' },
    { 'question': 'MGNREGA जॉब कार्ड के लिए आवेदन कैसे करें?', 'answer': 'MGNREGA जॉब कार्ड के लिए ग्राम पंचायत में आवेदन करें। किसी भी ग्रामीण परिवार का वयस्क सदस्य आवेदन कर सकता है। आधार और पासपोर्ट फोटो लेकर जाएं। 15 दिनों के भीतर काम दिया जाना चाहिए।', 'language': 'hi', 'category': 'Social Welfare' },
    { 'question': 'डाकघर में कौन-कौन सी सेवाएं मिलती हैं?', 'answer': 'डाकघर में: स्पीड पोस्ट, रजिस्टर्ड पोस्ट, मनी ऑर्डर, आधार सेवाएं, पासपोर्ट आवेदन, बचत खाता, PPF, NSC, सुकन्या समृद्धि, डाक जीवन बीमा और India Post Payments Bank सेवाएं मिलती हैं।', 'language': 'hi', 'category': 'Post Office' },
    { 'question': 'स्पीड पोस्ट कैसे ट्रैक करें?', 'answer': 'Speed Post को indiapost.gov.in पर ट्रैकिंग नंबर से ट्रैक करें। 1800-112-011 टोल फ्री नंबर पर कॉल करें या 55352 पर SMS भेजें।', 'language': 'hi', 'category': 'Post Office' },
    { 'question': 'ड्राइविंग लाइसेंस के लिए आवेदन कैसे करें?', 'answer': 'लर्नर लाइसेंस के लिए sarathi.parivahan.gov.in पर आवेदन करें। लर्नर टेस्ट पास करने के 30 दिन बाद स्थायी लाइसेंस के लिए आवेदन करें। RTO में: आवेदन पत्र, आयु प्रमाण, पते का प्रमाण, चिकित्सा प्रमाण पत्र और फोटो लेकर जाएं।', 'language': 'hi', 'category': 'Transport' },
    { 'question': 'वाहन पंजीकरण कैसे करें?', 'answer': 'वाहन पंजीकरण के लिए Regional Transport Office जाएं। खरीद के समय डीलर आमतौर पर पंजीकरण करता है। उरिमई हस्तांतरण के लिए parivahan.gov.in या RTO में Form 29/30, बीमा, PUC प्रमाण पत्र और आधार लेकर जाएं।', 'language': 'hi', 'category': 'Transport' },
    { 'question': 'साइबर क्राइम की शिकायत कैसे करें?', 'answer': 'साइबर अपराध की शिकायत cybercrime.gov.in पर या 1930 पर करें। ऑनलाइन धोखाधड़ी, सोशल मीडिया दुरुपयोग और साइबर उत्पीड़न की शिकायत कर सकते हैं। 24 घंटे उपलब्ध है।', 'language': 'hi', 'category': 'Police & Legal' },
    { 'question': 'पुलिस क्लियरेंस सर्टिफिकेट कैसे प्राप्त करें?', 'answer': 'पुलिस क्लियरेंस सर्टिफिकेट (PCC) passportindia.gov.in या स्थानीय पुलिस थाने से प्राप्त करें। आधार, पते का प्रमाण और पासपोर्ट की प्रति आवश्यक है। 7-21 दिन का समय लगता है।', 'language': 'hi', 'category': 'Police & Legal' },
    { 'question': 'PMAY आवास योजना के लिए आवेदन कैसे करें?', 'answer': 'PMAY के लिए pmaymis.gov.in या नजदीकी कॉमन सर्विस सेंटर पर आवेदन करें। पात्रता: वार्षिक आय 18 लाख से कम। EWS/LIG श्रेणी को होम लोन पर 2.67 लाख तक की सब्सिडी मिलती है।', 'language': 'hi', 'category': 'Housing' },
    { 'question': 'संपत्ति कर ऑनलाइन कैसे भरें?', 'answer': 'संपत्ति कर अपने नगर निगम की वेबसाइट पर भरें। संपत्ति मूल्यांकन नंबर आवश्यक है। UPI, नेट बैंकिंग और कार्ड से भुगतान स्वीकार किया जाता है।', 'language': 'hi', 'category': 'Housing' },
    { 'question': 'जन धन खाता कैसे खोलें?', 'answer': 'PMJDY खाता किसी भी राष्ट्रीयकृत बैंक या डाकघर में आधार और पासपोर्ट फोटो के साथ खोलें। न्यूनतम बैलेंस की जरूरत नहीं। RuPay डेबिट कार्ड और 2 लाख रुपये का दुर्घटना बीमा मिलता है।', 'language': 'hi', 'category': 'Finance' },
    { 'question': 'मुद्रा लोन कैसे प्राप्त करें?', 'answer': 'PMMY मुद्रा लोन के लिए किसी भी बैंक, MFI या NBFC में आवेदन करें। कोई गारंटी नहीं चाहिए। तीन श्रेणियां: शिशु (50,000 तक), किशोर (5 लाख तक), तरुण (10 लाख तक)।', 'language': 'hi', 'category': 'Finance' },
    { 'question': 'सरकारी कार्यालय के खिलाफ शिकायत कैसे करें?', 'answer': 'सरकारी कार्यालय के खिलाफ pgportal.gov.in पर ऑनलाइन शिकायत करें। CM हेल्पलाइन के लिए अपने राज्य का नंबर डायल करें। RTI आवेदन rtionline.gov.in पर करें।', 'language': 'hi', 'category': 'Grievance' },

    # TELUGU (te)
    { 'question': 'భూమి రికార్డులు ఆన్‌లైన్‌లో ఎలా చూడాలి?', 'answer': 'ఆంధ్రప్రదేశ్‌లో meebhoomi.ap.gov.in మరియు తెలంగాణలో dharani.telangana.gov.in వెబ్‌సైట్‌లో భూమి రికార్డులు చూడవచ్చు. జిల్లా, మండలం మరియు గ్రామం పేరు ఎంచుకోండి. సర్వే నంబర్ లేదా ఖాతా నంబర్ ఇవ్వండి.', 'language': 'te', 'category': 'Revenue & Land' },
    { 'question': 'ఆస్తి నమోదుకు ఏ పత్రాలు అవసరం?', 'answer': 'ఆస్తి నమోదుకు: అమ్మకపు పత్రం, ఎన్‌కంబ్రెన్స్ సర్టిఫికేట్, ఆధార్ కార్డు, PAN కార్డు, పాస్‌పోర్ట్ ఫోటోలు మరియు ఆస్తి పన్ను రసీదు అవసరం. స్టాంపు డ్యూటీ మరియు నమోదు రుసుము చెల్లించాలి.', 'language': 'te', 'category': 'Revenue & Land' },
    { 'question': 'కొత్త నీటి కనెక్షన్ ఎలా పొందాలి?', 'answer': 'కొత్త నీటి కనెక్షన్ కోసం స్థానిక మునిసిపాలిటీ లేదా TWAD బోర్డు కార్యాలయంలో దరఖాస్తు చేయండి. అవసరమైన పత్రాలు: దరఖాస్తు పత్రం, ఆధార్, ఆస్తి పన్ను రసీదు, చిరునామా రుజువు. ప్రక్రియ 15-30 రోజులు పట్టవచ్చు.', 'language': 'te', 'category': 'Water Supply' },
    { 'question': 'ప్రభుత్వ ఆసుపత్రిలో OPD లో నమోదు ఎలా చేయాలి?', 'answer': 'ప్రభుత్వ ఆసుపత్రిలో OPD నమోదుకు ఆధార్ కార్డుతో OPD కౌంటర్‌కు వెళ్ళండి. నమోదు ఉచితం. టోకెన్లు పరిమితంగా ఉంటాయి కాబట్టి ముందుగా వెళ్ళండి.', 'language': 'te', 'category': 'Health' },
    { 'question': 'ఆయుష్మాన్ భారత్ కార్డు ఎలా పొందాలి?', 'answer': 'ఆయుష్మాన్ భారత్ కార్డు కోసం దగ్గరలో ఉన్న కామన్ సర్వీస్ సెంటర్ లేదా ప్రభుత్వ ఆసుపత్రిలో దరఖాస్తు చేయండి. ఆధార్ మరియు రేషన్ కార్డు తీసుకెళ్ళండి. pmjay.gov.in లో అర్హత తనిఖీ చేయండి. 5 లక్షల రూపాయల వరకు ఆరోగ్య బీమా అందిస్తుంది.', 'language': 'te', 'category': 'Health' },
    { 'question': 'యాంబులెన్స్ ఎలా పిలవాలి?', 'answer': '108 డయల్ చేసి ఉచిత ప్రభుత్వ యాంబులెన్స్ సేవ పొందవచ్చు. ఈ సేవ 24 గంటలూ 7 రోజులూ అందుబాటులో ఉంటుంది.', 'language': 'te', 'category': 'Health' },
    { 'question': 'పాఠశాల నుండి బదిలీ సర్టిఫికెట్ ఎలా పొందాలి?', 'answer': 'బదిలీ సర్టిఫికెట్ కోసం పాఠశాల కార్యాలయంలో 7-10 రోజుల ముందు దరఖాస్తు చేయండి. అన్ని బకాయి ఫీజులు మరియు లైబ్రరీ పుస్తకాలు తిరిగి ఇవ్వండి. ప్రధానోపాధ్యాయుని సంతకం తర్వాత TC జారీ అవుతుంది. ఉచితం.', 'language': 'te', 'category': 'Education' },
    { 'question': 'ప్రభుత్వ స్కాలర్‌షిప్‌కు దరఖాస్తు ఎలా చేయాలి?', 'answer': 'ప్రభుత్వ స్కాలర్‌షిప్ కోసం scholarships.gov.in లో దరఖాస్తు చేయండి. SC/ST స్కాలర్‌షిప్, OBC స్కాలర్‌షిప్, మైనారిటీ స్కాలర్‌షిప్ అందుబాటులో ఉన్నాయి.', 'language': 'te', 'category': 'Education' },
    { 'question': 'PM కిసాన్ పేమెంట్ స్థితి ఎలా తనిఖీ చేయాలి?', 'answer': 'pmkisan.gov.in లో Beneficiary Status లో ఆధార్ నంబర్, ఖాతా నంబర్ లేదా మొబైల్ నంబర్ ద్వారా PM కిసాన్ స్థితి తనిఖీ చేయవచ్చు. అర్హులైన రైతులకు సంవత్సరానికి రూ.6000 మూడు వాయిదాలలో అందిస్తారు.', 'language': 'te', 'category': 'Agriculture' },
    { 'question': 'వితంతు పెన్షన్‌కు దరఖాస్తు ఎలా చేయాలి?', 'answer': 'వితంతు పెన్షన్ కోసం మునిసిపాలిటీ కార్యాలయం లేదా పంచాయితీలో దరఖాస్తు చేయండి. భర్త మరణ ధృవీకరణ పత్రం, ఆధార్, రేషన్ కార్డు, బ్యాంక్ పాస్‌బుక్ మరియు వయసు రుజువు తీసుకెళ్ళండి.', 'language': 'te', 'category': 'Social Welfare' },
    { 'question': 'పోస్ట్ ఆఫీసులో ఏ సేవలు అందుబాటులో ఉన్నాయి?', 'answer': 'పోస్ట్ ఆఫీసులో: స్పీడ్ పోస్ట్, రిజిస్టర్డ్ పోస్ట్, మనీ ఆర్డర్, ఆధార్ సేవలు, పాస్‌పోర్ట్ దరఖాస్తు, సేవింగ్స్ అకౌంట్, PPF, NSC, సుకన్య సమృద్ధి, పోస్టల్ లైఫ్ ఇన్సూరెన్స్ మరియు IPPB సేవలు అందుబాటులో ఉన్నాయి.', 'language': 'te', 'category': 'Post Office' },
    { 'question': 'వాహన నమోదు ఎలా చేయాలి?', 'answer': 'వాహన నమోదు RTO కార్యాలయంలో చేయాలి. కొనుగోలు సమయంలో డీలర్ సాధారణంగా నమోదు చేస్తారు. యజమాని మార్పుకు parivahan.gov.in లేదా RTO కార్యాలయంలో Form 29/30, బీమా, PUC సర్టిఫికెట్ మరియు ఆధార్ తీసుకెళ్ళండి.', 'language': 'te', 'category': 'Transport' },
    { 'question': 'సైబర్ క్రైమ్ ఫిర్యాదు ఎలా చేయాలి?', 'answer': 'సైబర్ నేరాలను cybercrime.gov.in లో లేదా 1930 కు కాల్ చేసి నివేదించండి. ఆన్‌లైన్ మోసం, సోషల్ మీడియా దుర్వినియోగం మరియు సైబర్ వేధింపులను నివేదించవచ్చు.', 'language': 'te', 'category': 'Police & Legal' },
    { 'question': 'PMAY గృహ పథకానికి దరఖాస్తు ఎలా చేయాలి?', 'answer': 'pmaymis.gov.in లేదా దగ్గరలో ఉన్న కామన్ సర్వీస్ సెంటర్‌లో PMAY కు దరఖాస్తు చేయండి. అర్హత: వార్షిక ఆదాయం రూ.18 లక్షలు కంటే తక్కువ. EWS/LIG వర్గాలకు గృహ రుణంపై రూ.2.67 లక్షల వరకు సబ్సిడీ అందిస్తారు.', 'language': 'te', 'category': 'Housing' },
    { 'question': 'జన్ ధన్ ఖాతా ఎలా తెరవాలి?', 'answer': 'ఏదైనా జాతీయమయం చేయబడిన బ్యాంకు లేదా పోస్ట్ ఆఫీసులో ఆధార్ మరియు పాస్‌పోర్ట్ ఫోటోతో PMJDY ఖాతా తెరవండి. కనీస బ్యాలెన్స్ అవసరం లేదు. RuPay డెబిట్ కార్డు మరియు రూ.2 లక్షల ప్రమాద బీమా అందిస్తారు.', 'language': 'te', 'category': 'Finance' },
    { 'question': 'ప్రభుత్వ కార్యాలయంపై ఫిర్యాదు ఎలా చేయాలి?', 'answer': 'pgportal.gov.in లో ఆన్‌లైన్‌లో ఫిర్యాదు చేయండి. CM హెల్‌లైన్ కోసం మీ రాష్ట్ర నంబర్‌కు కాల్ చేయండి.', 'language': 'te', 'category': 'Grievance' },

    # MALAYALAM (ml)
    { 'question': 'ഭൂമി രേഖകൾ ഓൺലൈനിൽ എങ്ങനെ കാണാം?', 'answer': 'കേരളത്തിൽ erekha.kerala.gov.in വെബ്‌സൈറ്റ് സന്ദർശിക്കുക. ജില്ല, താലൂക്ക്, വില്ലേജ് തിരഞ്ഞെടുക്കുക. സർവേ നമ്പർ അല്ലെങ്കിൽ ഉടമസ്ഥന്റെ പേർ നൽകുക. ഭൂമി രേഖകൾ ഡൗൺലോഡ് ചെയ്യാം.', 'language': 'ml', 'category': 'Revenue & Land' },
    { 'question': 'സ്വത്ത് രജിസ്ട്രേഷനു എന്ത് രേഖകൾ വേണം?', 'answer': 'സ്വത്ത് രജിസ്ട്രേഷനു: വില്പന ആധാരം, എൻകംബ്രൻസ് സർട്ടിഫിക്കറ്റ്, ആധാർ കാർഡ്, PAN കാർഡ്, പാസ്‌പോർട്ട് ഫോട്ടോ, സ്വത്ത് നികുതി രസീത് ആവശ്യമാണ്. സ്റ്റാമ്പ് ഡ്യൂട്ടിയും രജിസ്ട്രേഷൻ ഫീസും അടയ്ക്കണം.', 'language': 'ml', 'category': 'Revenue & Land' },
    { 'question': 'പൈപ്പ് ചോർച്ച എങ്ങനെ പരാതി നൽകാം?', 'answer': 'പൈപ്പ് ചോർച്ചയ്ക്ക് കേരള വാട്ടർ അതോറിറ്റി ഹെൽപ്‌ലൈൻ 1916 ൽ വിളിക്കുക. KWA വെബ്‌സൈറ്റ് kwa.kerala.gov.in ൽ ഓൺലൈൻ പരാതി നൽകാം. Fix My Street പോർട്ടലും ഉപയോഗിക്കാം.', 'language': 'ml', 'category': 'Water Supply' },
    { 'question': 'ആംബുലൻസ് എങ്ങനെ വിളിക്കാം?', 'answer': '108 ഡയൽ ചെയ്ത് സൗജന്യ ഗവൺമെന്റ് ആംബുലൻസ് സേവനം പ്രയോജനപ്പെടുത്താം. ഈ സേവനം 24 മണിക്കൂറും ആഴ്ചയിൽ 7 ദിവസവും ലഭ്യമാണ്.', 'language': 'ml', 'category': 'Health' },
    { 'question': 'ആയുഷ്മാൻ ഭാരത് കാർഡ് എങ്ങനെ ലഭിക്കും?', 'answer': 'ആയുഷ്മാൻ ഭാരത് കാർഡിനു അടുത്തുള്ള കോമൺ സർവീസ് സെന്ററിൽ അല്ലെങ്കിൽ ഗവൺമെന്റ് ആശുപത്രിയിൽ അപേക്ഷിക്കുക. ആധാർ കാർഡും റേഷൻ കാർഡും കൊണ്ടുപോകുക. 5 ലക്ഷം രൂപ വരെ ആരോഗ്യ ഇൻഷൂറൻസ് ലഭിക്കും.', 'language': 'ml', 'category': 'Health' },
    { 'question': 'വൈകല്യ സർട്ടിഫിക്കറ്റ് എങ്ങനെ ലഭിക്കും?', 'answer': 'വൈകല്യ സർട്ടിഫിക്കറ്റിനു ഗവൺമെന്റ് ആശുപത്രിയിൽ മെഡിക്കൽ ബോർഡ് മുൻപാകെ അപേക്ഷിക്കുക. RPWD Act 2016 പ്രകാരം Form IV പൂരിപ്പിക്കുക. ആധാർ, മെഡിക്കൽ രേഖകൾ, ഫോട്ടോ ആവശ്യമാണ്.', 'language': 'ml', 'category': 'Health' },
    { 'question': 'സ്കൂൾ സ്കോളർഷിപ്പിനു എങ്ങനെ അപേക്ഷിക്കാം?', 'answer': 'സർക്കാർ സ്കോളർഷിപ്പിനു scholarships.gov.in ൽ അപേക്ഷിക്കുക. SC/ST, OBC, ന്യൂനപക്ഷ, മെറിറ്റ് സ്കോളർഷിപ്പ് ലഭ്യമാണ്. ആധാർ, വരുമാന സർട്ടിഫിക്കറ്റ്, ജാതി സർട്ടിഫിക്കറ്റ് ആവശ്യമാണ്.', 'language': 'ml', 'category': 'Education' },
    { 'question': 'PM കിസാൻ പേമെന്റ് സ്ഥിതി എങ്ങനെ പരിശോധിക്കാം?', 'answer': 'pmkisan.gov.in ൽ Beneficiary Status ൽ ആധാർ നമ്പർ, അക്കൗണ്ട് നമ്പർ അല്ലെങ്കിൽ മൊബൈൽ നമ്പർ ഉപയോഗിച്ച് PM കിസാൻ സ്ഥിതി പരിശോധിക്കാം. യോഗ്യരായ കർഷകർക്ക് വർഷം 6000 രൂപ മൂന്ന് ഗഡുക്കളായി ലഭിക്കും.', 'language': 'ml', 'category': 'Agriculture' },
    { 'question': 'MGNREGA ജോബ് കാർഡ് എങ്ങനെ ലഭിക്കും?', 'answer': 'MGNREGA ജോബ് കാർഡിനു ഗ്രാമ പഞ്ചായത്തിൽ അപേക്ഷിക്കുക. ഏതൊരു ഗ്രാമീണ കുടുംബ മുതിർന്ന അംഗത്തിനും അപേക്ഷിക്കാം. ആധാർ, ഫോട്ടോ ആവശ്യമാണ്. 15 ദിവസത്തിനകം തൊഴിൽ നൽകണം.', 'language': 'ml', 'category': 'Social Welfare' },
    { 'question': 'സ്പീഡ് പോസ്റ്റ് ട്രാക്ക് ചെയ്യുന്നത് എങ്ങനെ?', 'answer': 'indiapost.gov.in ൽ ട്രാക്കിംഗ് നമ്പർ ഉപയോഗിച്ച് Speed Post ട്രാക്ക് ചെയ്യാം. 1800-112-011 ടോൾ ഫ്രീ നമ്പറിൽ വിളിക്കാം അല്ലെങ്കിൽ 55352 ൽ SMS അയക്കാം.', 'language': 'ml', 'category': 'Post Office' },
    { 'question': 'ഡ്രൈവിംഗ് ലൈസൻസിനു അപേക്ഷിക്കുന്നത് എങ്ങനെ?', 'answer': 'ലേണർ ലൈസൻസിനു sarathi.parivahan.gov.in ൽ അപേക്ഷിക്കുക. ലേണർ ടെസ്റ്റ് വിജയിച്ച് 30 ദിവസം കഴിഞ്ഞ് സ്ഥിര ലൈസൻസിനു അപേക്ഷിക്കുക. ആയ സർട്ടിഫിക്കറ്റ്, വിലാസ തെളിവ്, മെഡിക്കൽ സർട്ടിഫിക്കറ്റ്, ഫോട്ടോ ആവശ്യം.', 'language': 'ml', 'category': 'Transport' },
    { 'question': 'സൈബർ കുറ്റകൃത്യം റിപ്പോർട്ട് ചെയ്യുന്നത് എങ്ങനെ?', 'answer': 'സൈബർ കുറ്റകൃത്യങ്ങൾ cybercrime.gov.in ൽ റിപ്പോർട്ട് ചെയ്യുക അല്ലെങ്കിൽ 1930 ൽ വിളിക്കുക. ഓൺലൈൻ തട്ടിപ്പ്, സോഷ്യൽ മീഡിയ ദുരുപയോഗം, സൈബർ പീഡനം റിപ്പോർട്ട് ചെയ്യാം.', 'language': 'ml', 'category': 'Police & Legal' },
    { 'question': 'PMAY ഭവന പദ്ധതിക്ക് അപേക്ഷിക്കുന്നത് എങ്ങനെ?', 'answer': 'pmaymis.gov.in ൽ അല്ലെങ്കിൽ അടുത്തുള്ള കോമൺ സർവീസ് സെന്ററിൽ PMAY ക്ക് അപേക്ഷിക്കുക. യോഗ്യത: വാർഷിക വരുമാനം 18 ലക്ഷം രൂപയിൽ കുറവ്. EWS/LIG വിഭാഗക്കാർക്ക് 2.67 ലക്ഷം രൂപ വരെ സബ്സിഡി.', 'language': 'ml', 'category': 'Housing' },
    { 'question': 'മുദ്ര ലോൺ എങ്ങനെ ലഭിക്കും?', 'answer': 'ഏതൊരു ബാങ്ക്, MFI അല്ലെങ്കിൽ NBFC ൽ PMMY മുദ്ര ലോണിനു അപേക്ഷിക്കുക. ഗ്യാരന്റി ആവശ്യമില്ല. മൂന്ന് വിഭാഗങ്ങൾ: ശിശു (50,000 വരെ), കിഷോർ (5 ലക്ഷം വരെ), തരുൺ (10 ലക്ഷം വരെ).', 'language': 'ml', 'category': 'Finance' },
    { 'question': 'സർക്കാർ ഓഫീസിനെതിരെ പരാതി നൽകുന്നത് എങ്ങനെ?', 'answer': 'pgportal.gov.in ൽ ഓൺലൈൻ പരാതി നൽകുക. CM ഹെൽപ്‌ലൈനിനു നിങ്ങളുടെ സംസ്ഥാന നമ്പർ ഡയൽ ചെയ്യുക. RTI അപേക്ഷ rtionline.gov.in ൽ ഫയൽ ചെയ്യാം.', 'language': 'ml', 'category': 'Grievance' },

    # KANNADA (kn)
    { 'question': 'ಭೂಮಿ ದಾಖಲೆಗಳನ್ನು ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಹೇಗೆ ನೋಡುವುದು?', 'answer': 'ಕರ್ನಾಟಕದಲ್ಲಿ landrecords.karnataka.gov.in ವೆಬ್‌ಸೈಟ್ ಸಂದರ್ಶಿಸಿ. ಜಿಲ್ಲೆ, ತಾಲ್ಲೂಕು ಮತ್ತು ಹೋಬಳಿ ಆಯ್ಕೆ ಮಾಡಿ. ಸರ್ವೆ ನಂಬರ್ ಅಥವಾ ಮಾಲೀಕರ ಹೆಸರು ನಮೂದಿಸಿ. ಭೂಮಿ ದಾಖಲೆಗಳನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.', 'language': 'kn', 'category': 'Revenue & Land' },
    { 'question': 'ನೀರಿನ ಪೈಪ್ ಸೋರಿಕೆ ಬಗ್ಗೆ ಹೇಗೆ ದೂರು ನೀಡುವುದು?', 'answer': 'ನೀರಿನ ಪೈಪ್ ಸೋರಿಕೆ ದೂರಿಗಾಗಿ ನಗರಪಾಲಿಕೆ ಸಹಾಯವಾಣಿ ಅಥವಾ ಸ್ಥಳೀಯ ಜಲಮಂಡಳಿ ಕಚೇರಿಗೆ ಸಂಪರ್ಕಿಸಿ. Fix My Street ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ದೂರು ನೋಂದಾಯಿಸಬಹುದು.', 'language': 'kn', 'category': 'Water Supply' },
    { 'question': 'ಆಂಬ್ಯುಲೆನ್ಸ್ ಅನ್ನು ಹೇಗೆ ಕರೆಯುವುದು?', 'answer': '108 ಡಯಲ್ ಮಾಡಿ ಉಚಿತ ಸರ್ಕಾರಿ ಆಂಬ್ಯುಲೆನ್ಸ್ ಸೇವೆ ಪಡೆಯಬಹುದು. ಈ ಸೇವೆ 24 ಗಂಟೆ 7 ದಿನ ಲಭ್ಯವಿದೆ.', 'language': 'kn', 'category': 'Health' },
    { 'question': 'ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಕಾರ್ಡ್ ಹೇಗೆ ಪಡೆಯುವುದು?', 'answer': 'ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಕಾರ್ಡ್‌ಗಾಗಿ ಹತ್ತಿರದ ಕಾಮನ್ ಸರ್ವೀಸ್ ಸೆಂಟರ್ ಅಥವಾ ಸರ್ಕಾರಿ ಆಸ್ಪತ್ರೆಯಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ. ಆಧಾರ್ ಮತ್ತು ರೇಷನ್ ಕಾರ್ಡ್ ತೆಗೆದುಕೊಂಡು ಹೋಗಿ. 5 ಲಕ್ಷ ರೂಪಾಯಿವರೆಗೆ ಆರೋಗ್ಯ ವಿಮೆ ಸಿಗುತ್ತದೆ.', 'language': 'kn', 'category': 'Health' },
    { 'question': 'ಸರ್ಕಾರಿ ವಿದ್ಯಾರ್ಥಿ ವೇತನಕ್ಕೆ ಅರ್ಜಿ ಹೇಗೆ ಸಲ್ಲಿಸುವುದು?', 'answer': 'ಸರ್ಕಾರಿ ವಿದ್ಯಾರ್ಥಿ ವೇತನಕ್ಕೆ scholarships.gov.in ನಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ. SC/ST, OBC, ಅಲ್ಪಸಂಖ್ಯಾತ ವಿದ್ಯಾರ್ಥಿ ವೇತನ ಲಭ್ಯವಿದೆ. ಆಧಾರ್, ಆದಾಯ ಪ್ರಮಾಣ ಪತ್ರ, ಜಾತಿ ಪ್ರಮಾಣ ಪತ್ರ ಅಗತ್ಯ.', 'language': 'kn', 'category': 'Education' },
    { 'question': 'ಪಿಎಂ ಕಿಸಾನ್ ಹಣ ಬಂದಿದೆಯೇ ಎಂದು ಹೇಗೆ ತಿಳಿಯುವುದು?', 'answer': 'pmkisan.gov.in ನಲ್ಲಿ Beneficiary Status ಅಡಿಯಲ್ಲಿ ಆಧಾರ್ ಸಂಖ್ಯೆ, ಖಾತೆ ಸಂಖ್ಯೆ ಅಥವಾ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯಿಂದ ಪರಿಶೀಲಿಸಿ. ಅರ್ಹ ರೈತರಿಗೆ ವರ್ಷಕ್ಕೆ 6000 ರೂಪಾಯಿ ಮೂರು ಕಂತುಗಳಲ್ಲಿ ನೀಡಲಾಗುತ್ತದೆ.', 'language': 'kn', 'category': 'Agriculture' },
    { 'question': 'ವಿಧವಾ ವೇತನಕ್ಕೆ ಅರ್ಜಿ ಹೇಗೆ ಸಲ್ಲಿಸುವುದು?', 'answer': 'ವಿಧವಾ ವೇತನಕ್ಕೆ ನಗರಪಾಲಿಕೆ ಕಚೇರಿ ಅಥವಾ ಪಂಚಾಯತ್‌ನಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ. ಪತಿಯ ಮರಣ ಪ್ರಮಾಣ ಪತ್ರ, ಆಧಾರ್, ರೇಷನ್ ಕಾರ್ಡ್, ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ಮತ್ತು ವಯಸ್ಸಿನ ಪುರಾವೆ ತೆಗೆದುಕೊಂಡು ಹೋಗಿ.', 'language': 'kn', 'category': 'Social Welfare' },
    { 'question': 'ಅಂಚೆ ಕಚೇರಿಯಲ್ಲಿ ಯಾವ ಸೇವೆಗಳು ಲಭ್ಯವಿದೆ?', 'answer': 'ಅಂಚೆ ಕಚೇರಿಯಲ್ಲಿ: ಸ್ಪೀಡ್ ಪೋಸ್ಟ್, ರಿಜಿಸ್ಟರ್ಡ್ ಪೋಸ್ಟ್, ಮನಿ ಆರ್ಡರ್, ಆಧಾರ್ ಸೇವೆಗಳು, ಪಾಸ್‌ಪೋರ್ಟ್ ಅರ್ಜಿ, ಉಳಿತಾಯ ಖಾತೆ, PPF, NSC, ಸುಕನ್ಯ ಸಮೃದ್ಧಿ, ಅಂಚೆ ಜೀವ ವಿಮೆ ಮತ್ತು IPPB ಸೇವೆಗಳು ಲಭ್ಯ.', 'language': 'kn', 'category': 'Post Office' },
    { 'question': 'ವಾಹನ ನೋಂದಣಿ ಹೇಗೆ ಮಾಡುವುದು?', 'answer': 'ವಾಹನ ನೋಂದಣಿ ಪ್ರಾದೇಶಿಕ ಸಾರಿಗೆ ಕಚೇರಿ (RTO) ನಲ್ಲಿ ಮಾಡಲಾಗುತ್ತದೆ. ಖರೀದಿ ಸಮಯದಲ್ಲಿ ಡೀಲರ್ ಸಾಮಾನ್ಯವಾಗಿ ನೋಂದಣಿ ಮಾಡಿಸುತ್ತಾರೆ. ಮಾಲೀಕತ್ವ ವರ್ಗಾವಣೆಗೆ parivahan.gov.in ಅಥವಾ RTO ಕಚೇರಿಗೆ ಹೋಗಿ.', 'language': 'kn', 'category': 'Transport' },
    { 'question': 'ಸೈಬರ್ ಅಪರಾಧ ಹೇಗೆ ದೂರು ನೀಡುವುದು?', 'answer': 'ಸೈಬರ್ ಅಪರಾಧಗಳನ್ನು cybercrime.gov.in ನಲ್ಲಿ ದೂರು ನೀಡಿ ಅಥವಾ 1930 ಕರೆ ಮಾಡಿ. ಆನ್‌ಲೈನ್ ಮೋಸ, ಸಾಮಾಜಿಕ ಮಾಧ್ಯಮ ದುರ್ಬಳಕೆ ದೂರು ನೀಡಬಹುದು.', 'language': 'kn', 'category': 'Police & Legal' },
    { 'question': 'PMAY ಹೌಸಿಂಗ್ ಯೋಜನೆಗೆ ಅರ್ಜಿ ಹೇಗೆ ಸಲ್ಲಿಸುವುದು?', 'answer': 'pmaymis.gov.in ಅಥವಾ ಹತ್ತಿರದ ಕಾಮನ್ ಸರ್ವೀಸ್ ಸೆಂಟರ್‌ನಲ್ಲಿ PMAY ಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ. ಅರ್ಹತೆ: ವಾರ್ಷಿಕ ಆದಾಯ 18 ಲಕ್ಷ ರೂಪಾಯಿಗಿಂತ ಕಡಿಮೆ. EWS/LIG ವರ್ಗಕ್ಕೆ ಗೃಹ ಸಾಲದ ಮೇಲೆ 2.67 ಲಕ್ಷ ರೂಪಾಯಿವರೆಗೆ ಸಬ್ಸಿಡಿ.', 'language': 'kn', 'category': 'Housing' },
    { 'question': 'ಜನ ಧನ್ ಖಾತೆ ಹೇಗೆ ತೆರೆಯುವುದು?', 'answer': 'ಯಾವುದೇ ರಾಷ್ಟ್ರೀಕರಣ ಬ್ಯಾಂಕ್ ಅಥವಾ ಅಂಚೆ ಕಚೇರಿಯಲ್ಲಿ ಆಧಾರ್ ಮತ್ತು ಪಾಸ್‌ಪೋರ್ಟ್ ಫೋಟೋದೊಂದಿಗೆ PMJDY ಖಾತೆ ತೆರೆಯಿರಿ. ಕನಿಷ್ಠ ಬ್ಯಾಲೆನ್ಸ್ ಬೇಕಿಲ್ಲ. RuPay ಡೆಬಿಟ್ ಕಾರ್ಡ್ ಮತ್ತು 2 ಲಕ್ಷ ರೂಪಾಯಿ ಅಪಘಾತ ವಿಮೆ ಸಿಗುತ್ತದೆ.', 'language': 'kn', 'category': 'Finance' },
    { 'question': 'ಸರ್ಕಾರಿ ಕಚೇರಿ ವಿರುದ್ಧ ದೂರು ಹೇಗೆ ನೀಡುವುದು?', 'answer': 'pgportal.gov.in ನಲ್ಲಿ ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ದೂರು ನೀಡಿ. CM ಸಹಾಯವಾಣಿಗೆ ನಿಮ್ಮ ರಾಜ್ಯದ ಸಂಖ್ಯೆ ಡಯಲ್ ಮಾಡಿ.', 'language': 'kn', 'category': 'Grievance' },

    # BENGALI (bn)
    { 'question': 'জমির রেকর্ড অনলাইনে কীভাবে দেখবেন?', 'answer': 'পশ্চিমবঙ্গে banglarbhumi.gov.in ওয়েবসাইটে জমির রেকর্ড দেখা যায়। জেলা, ব্লক এবং মৌজা নির্বাচন করুন। খতিয়ান নম্বর বা দাগ নম্বর দিন। পর্চা ডাউনলোড করুন।', 'language': 'bn', 'category': 'Revenue & Land' },
    { 'question': 'সম্পত্তি নিবন্ধনের জন্য কী কী কাগজপত্র দরকার?', 'answer': 'সম্পত্তি নিবন্ধনের জন্য: বিক্রয় দলিল, এনকাম্ব্রেন্স সার্টিফিকেট, আধার কার্ড, PAN কার্ড, পাসপোর্ট ফটো এবং সম্পত্তি কর রসিদ দরকার। স্ট্যাম্প ডিউটি এবং রেজিস্ট্রেশন ফি পরিশোধ করতে হবে।', 'language': 'bn', 'category': 'Revenue & Land' },
    { 'question': 'নতুন জলের সংযোগ কীভাবে নেবেন?', 'answer': 'নতুন জল সংযোগের জন্য স্থানীয় পৌরসভা বা জল বোর্ড অফিসে আবেদন করুন। প্রয়োজনীয় কাগজপত্র: আবেদনপত্র, আধার কার্ড, সম্পত্তি কর রসিদ, ঠিকানার প্রমাণ। ১৫-৩০ দিনের মধ্যে সংযোগ পাবেন।', 'language': 'bn', 'category': 'Water Supply' },
    { 'question': 'সরকারি হাসপাতালে OPD তে কীভাবে নিবন্ধন করবেন?', 'answer': 'সরকারি হাসপাতালে OPD নিবন্ধনের জন্য আধার কার্ড নিয়ে OPD কাউন্টারে যান। নিবন্ধন বিনামূল্যে। টোকেন সীমিত তাই সকালে তাড়াতাড়ি যান।', 'language': 'bn', 'category': 'Health' },
    { 'question': 'অ্যাম্বুলেন্স কীভাবে ডাকবেন?', 'answer': '108 নম্বরে ফোন করে বিনামূল্যে সরকারি অ্যাম্বুলেন্স পাওয়া যাবে। এই সেবা ২৪ ঘণ্টা ৭ দিন পাওয়া যায়।', 'language': 'bn', 'category': 'Health' },
    { 'question': 'আয়ুষ্মান ভারত কার্ড কীভাবে পাবেন?', 'answer': 'আয়ুষ্মান ভারত কার্ডের জন্য কাছের কমন সার্ভিস সেন্টার বা সরকারি হাসপাতালে আবেদন করুন। আধার ও রেশন কার্ড নিয়ে যান। pmjay.gov.in এ যোগ্যতা যাচাই করুন। ৫ লাখ টাকা পর্যন্ত স্বাস্থ্য বিমা পাবেন।', 'language': 'bn', 'category': 'Health' },
    { 'question': 'স্কুল থেকে ট্রান্সফার সার্টিফিকেট কীভাবে নেবেন?', 'answer': 'ট্রান্সফার সার্টিফিকেটের জন্য স্কুল অফিসে ৭-১০ দিন আগে আবেদন করুন। সমস্ত বকেয়া ফি এবং লাইব্রেরি বই জমা দিন। প্রধান শিক্ষকের স্বাক্ষরের পর TC জারি হবে। বিনামূল্যে।', 'language': 'bn', 'category': 'Education' },
    { 'question': 'সরকারি বৃত্তির জন্য কীভাবে আবেদন করবেন?', 'answer': 'সরকারি বৃত্তির জন্য scholarships.gov.in এ আবেদন করুন। SC/ST, OBC, সংখ্যালঘু এবং মেধা বৃত্তি পাওয়া যায়। আধার, আয়ের প্রমাণ এবং জাতি সনদ দরকার।', 'language': 'bn', 'category': 'Education' },
    { 'question': 'PM কিসান এর টাকা এসেছে কিনা কীভাবে চেক করবেন?', 'answer': 'pmkisan.gov.in এ Beneficiary Status এ আধার নম্বর, অ্যাকাউন্ট নম্বর বা মোবাইল নম্বর দিয়ে PM কিসান অবস্থা যাচাই করুন। যোগ্য কৃষকরা বছরে ৬০০০ টাকা তিন কিস্তিতে পান।', 'language': 'bn', 'category': 'Agriculture' },
    { 'question': 'ফসল বিমার জন্য কীভাবে আবেদন করবেন?', 'answer': 'ফসল বিমার (PMFBY) জন্য কাছের ব্যাংক, কমন সার্ভিস সেন্টার বা pmfby.gov.in এ আবেদন করুন। রবি ফসলে ১.৫% এবং খারিফে ২% প্রিমিয়াম।', 'language': 'bn', 'category': 'Agriculture' },
    { 'question': 'MGNREGA জব কার্ডের জন্য কীভাবে আবেদন করবেন?', 'answer': 'MGNREGA জব কার্ডের জন্য গ্রাম পঞ্চায়েতে আবেদন করুন। যেকোনো গ্রামীণ পরিবারের প্রাপ্তবয়স্ক সদস্য আবেদন করতে পারবেন। আধার এবং পাসপোর্ট ফটো লাগবে।', 'language': 'bn', 'category': 'Social Welfare' },
    { 'question': 'ডাকঘরে কী কী সেবা পাওয়া যায়?', 'answer': 'ডাকঘরে: স্পিড পোস্ট, রেজিস্টার্ড পোস্ট, মানি অর্ডার, আধার সেবা, পাসপোর্ট আবেদন, সঞ্চয় অ্যাকাউন্ট, PPF, NSC, সুকন্যা সমৃদ্ধি, ডাক জীবন বিমা এবং IPPB সেবা পাওয়া যায়।', 'language': 'bn', 'category': 'Post Office' },
    { 'question': 'ড্রাইভিং লাইসেন্সের জন্য কীভাবে আবেদন করবেন?', 'answer': 'শিক্ষানবিশ লাইসেন্সের জন্য sarathi.parivahan.gov.in এ আবেদন করুন। শিক্ষানবিশ পরীক্ষায় পাস করার ৩০ দিন পর স্থায়ী লাইসেন্সের জন্য আবেদন করুন।', 'language': 'bn', 'category': 'Transport' },
    { 'question': 'সাইবার অপরাধের অভিযোগ কীভাবে করবেন?', 'answer': 'সাইবার অপরাধের অভিযোগ cybercrime.gov.in এ করুন অথবা 1930 এ ফোন করুন। অনলাইন প্রতারণা, সোশ্যাল মিডিয়া অপব্যবহার এবং সাইবার হয়রানির অভিযোগ করা যাবে।', 'language': 'bn', 'category': 'Police & Legal' },
    { 'question': 'PMAY আবাসন প্রকল্পে কীভাবে আবেদন করবেন?', 'answer': 'pmaymis.gov.in বা কাছের কমন সার্ভিস সেন্টারে PMAY এর জন্য আবেদন করুন। যোগ্যতা: বার্ষিক আয় ১৮ লাখ টাকার কম। EWS/LIG বিভাগে গৃহঋণে ২.৬৭ লাখ টাকা পর্যন্ত ভর্তুকি পাওয়া যায়।', 'language': 'bn', 'category': 'Housing' },
    { 'question': 'মুদ্রা লোন কীভাবে পাবেন?', 'answer': 'যেকোনো ব্যাংক, MFI বা NBFC তে PMMY মুদ্রা লোনের জন্য আবেদন করুন। জামানত দরকার নেই। তিনটি বিভাগ: শিশু (৫০,০০০ পর্যন্ত), কিশোর (৫ লাখ পর্যন্ত), তরুণ (১০ লাখ পর্যন্ত)।', 'language': 'bn', 'category': 'Finance' },
    { 'question': 'সরকারি অফিসের বিরুদ্ধে অভিযোগ কীভাবে করবেন?', 'answer': 'pgportal.gov.in এ অনলাইনে অভিযোগ করুন। CM হেল্পলাইনের জন্য আপনার রাজ্যের নম্বরে ফোন করুন। RTI আবেদন rtionline.gov.in এ করুন।', 'language': 'bn', 'category': 'Grievance' },

    # MARATHI (mr)
    { 'question': 'जमिनीचे ७/१२ उतारा ऑनलाइन कसा काढायचा?', 'answer': 'महाराष्ट्रात bhulekh.mahabhumi.gov.in वर जमिनीचा ७/१२ उतारा ऑनलाइन काढता येतो. जिल्हा, तालुका आणि गाव निवडा. सर्व्हे नंबर किंवा गट नंबर टाका. उतारा डाउनलोड करा.', 'language': 'mr', 'category': 'Revenue & Land' },
    { 'question': 'मालमत्ता नोंदणीसाठी कोणते कागदपत्रे लागतात?', 'answer': 'मालमत्ता नोंदणीसाठी: विक्री करार, एन्कम्ब्रन्स सर्टिफिकेट, आधार कार्ड, PAN कार्ड, पासपोर्ट फोटो आणि मालमत्ता कर पावती आवश्यक आहे. मुद्रांक शुल्क आणि नोंदणी शुल्क भरावे लागते.', 'language': 'mr', 'category': 'Revenue & Land' },
    { 'question': 'नवीन पाण्याचे कनेक्शन कसे घ्यायचे?', 'answer': 'नवीन जल कनेक्शनसाठी नगरपालिका किंवा महाराष्ट्र जीवन प्राधिकरण (MJP) कार्यालयात अर्ज करा. आधार कार्ड, मालमत्ता कर पावती, पत्त्याचा पुरावा आवश्यक. कनेक्शन १५-३० दिवसांत मिळते.', 'language': 'mr', 'category': 'Water Supply' },
    { 'question': 'रुग्णवाहिका कशी बोलवायची?', 'answer': '108 डायल करून मोफत सरकारी रुग्णवाहिका सेवा मिळवता येते. ही सेवा २४ तास ७ दिवस उपलब्ध आहे.', 'language': 'mr', 'category': 'Health' },
    { 'question': 'आयुष्मান भारत कार्ड कसे मिळवायचे?', 'answer': 'आयुष्मान भारत कार्डसाठी जवळच्या कॉमन सर्व्हिस सेंटर किंवा सरकारी रुग्णालयात अर्ज करा. आधार कार्ड आणि रेशन कार्ड घेऊन जा. pmjay.gov.in वर पात्रता तपासा. ५ लाखांपर्यंत आरोग्य विमा मिळतो.', 'language': 'mr', 'category': 'Health' },
    { 'question': 'अपंगत्व प्रमाणपत्र कसे मिळवायचे?', 'answer': 'अपंगत्व प्रमाणपत्रासाठी सरकारी रुग्णालयातील वैद्यकीय मंडळासमोर अर्ज करा. RPWD Act 2016 नुसार Form IV भरा. आधार, वैद्यकीय नोंदी आणि पासपोर्ट फोटो आवश्यक आहेत.', 'language': 'mr', 'category': 'Health' },
    { 'question': 'शाळेतून स्थलांतर दाखला कसा मिळवायचा?', 'answer': 'स्थलांतर दाखल्यासाठी शाळेच्या कार्यालयात ७-१० दिवस आधी अर्ज करा. सर्व थकीत फी आणि ग्रंथालयातील पुस्तके परत करा. मुख्याध्यापकांच्या स्वाक्षरीनंतर TC दिला जातो. मोफत आहे.', 'language': 'mr', 'category': 'Education' },
    { 'question': 'सरकारी शिष्यवृत्तीसाठी अर्ज कसा करायचा?', 'answer': 'सरकारी शिष्यवृत्तीसाठी scholarships.gov.in वर अर्ज करा. SC/ST, OBC, अल्पसंख्यांक आणि गुणवत्ता शिष्यवृत्ती उपलब्ध आहेत. आधार, उत्पन्न प्रमाणपत्र आणि जात प्रमाणपत्र आवश्यक आहे.', 'language': 'mr', 'category': 'Education' },
    { 'question': 'PM किसान पैसे आले का हे कसे तपासायचे?', 'answer': 'pmkisan.gov.in वर Beneficiary Status मध्ये आधार नंबर, खाते क्रमांक किंवा मोबाइल नंबरने PM किसान स्थिती तपासा. पात्र शेतकऱ्यांना वर्षाला ६००० रुपये तीन हप्त्यांमध्ये दिले जातात.', 'language': 'mr', 'category': 'Agriculture' },
    { 'question': 'पीक विमा योजनेसाठी अर्ज कसा करायचा?', 'answer': 'पीक विमा (PMFBY) साठी जवळच्या बँक, कॉमन सर्व्हिस सेंटर किंवा pmfby.gov.in वर अर्ज करा. रब्बीसाठी १.५% आणि खरीपसाठी २% प्रीमियम आहे.', 'language': 'mr', 'category': 'Agriculture' },
    { 'question': 'विधवा पेन्शनसाठी अर्ज कसा करायचा?', 'answer': 'विधवा पेन्शनसाठी नगरपालिका किंवा ग्रामपंचायत कार्यालयात अर्ज करा. पतीचे मृत्यू प्रमाणपत्र, आधार, रेशन कार्ड, बँक पासबुक आणि वयाचा पुरावा घेऊन जा.', 'language': 'mr', 'category': 'Social Welfare' },
    { 'question': 'MGNREGA जॉब कार्डसाठी अर्ज कसा करायचा?', 'answer': 'MGNREGA जॉब कार्डसाठी ग्रामपंचायतीत अर्ज करा. कोणत्याही ग्रामीण कुटुंबातील प्रौढ सदस्य अर्ज करू शकतो. आधार आणि पासपोर्ट फोटो आवश्यक आहे.', 'language': 'mr', 'category': 'Social Welfare' },
    { 'question': 'टपाल कार्यालयात कोणत्या सेवा मिळतात?', 'answer': 'टपाल कार्यालयात: स्पीड पोस्ट, नोंदणीकृत पोस्ट, मनी ऑर्डर, आधार सेवा, पासपोर्ट अर्ज, बचत खाते, PPF, NSC, सुकन्या समृद्धी, पोस्टल 라이फ इन्शुरन्स आणि IPPB सेवा मिळतात.', 'language': 'mr', 'category': 'Post Office' },
    { 'question': 'स्पीड पोस्ट कसे ट्रॅक करायचे?', 'answer': 'Speed Post indiapost.gov.in वर ट्रॅकिंग नंबरने ट्रॅक करा. 1800-112-011 टोल फ्री नंबरवर कॉल करा किंवा 55352 वर SMS पाठवा.', 'language': 'mr', 'category': 'Post Office' },
    { 'question': 'वाहन नोंदणी कशी करायची?', 'answer': 'वाहन नोंदणी प्रादेशिक परिवहन कार्यालयात (RTO) केली जाते. खरेदी वेळी डീലर सहसा नोंदणी करतो. मालकी हस्तांतरणासाठी parivahan.gov.in किंवा RTO कार्यालयात Form 29/30, विमा, PUC प्रमाणपत्र आणि आधार घेऊन जा.', 'language': 'mr', 'category': 'Transport' },
    { 'question': 'ड्रायव्हिंग लायसन्ससाठी अर्ज कसा करायचा?', 'answer': 'शिकाऊ लायसन्ससाठी sarathi.parivahan.gov.in वर अर्ज करा. शिकाऊ चाचणी उत्तीर्ण झाल्यानंतर ३० दिवसांनी कायमस्वरूपी लायसन्ससाठी अर्ज करा. वयाचा पुरावा, पत्त्याचा पुरावा, वैद्यकीय प्रमाणपत्र आणि फोटो आणा.', 'language': 'mr', 'category': 'Transport' },
    { 'question': 'FIR कशी नोंदवायची?', 'answer': 'FIR नोंदवण्यासाठी जवळच्या पोलिस ठाण्यात जा. कोणत्याही दखलपात्र गुन्ह्यासाठी FIR नोंदवणे पोलिसांचे कर्तव्य आहे. ऑनलाइन FIR साठी राज्य पोलिस वेबसाइटवर जा किंवा 100 डायल करा.', 'language': 'mr', 'category': 'Police & Legal' },
    { 'question': 'सायबर गुन्ह्याची तक्रार कशी करायची?', 'answer': 'सायबर गुन्ह्याची तक्रार cybercrime.gov.in वर करा किंवा 1930 वर कॉल करा. ऑनलाइन फसवणूक, सोशल मीडिया गैरवापर आणि सायबर छळाची तक्रार करता येते.', 'language': 'mr', 'category': 'Police & Legal' },
    { 'question': 'PMAY गृहयोजनेसाठी अर्ज कसा करायचा?', 'answer': 'pmaymis.gov.in किंवा जवळच्या कॉमन सर्व्हिस सेंटरमध्ये PMAY साठी अर्ज करा. पात्रता: वार्षिक उत्पन्न १८ लाखांपेक्षा कमी. EWS/LIG गटासाठी गृहकर्जावर २.67 लाखांपर्यंत अनुदान मिळते.', 'language': 'mr', 'category': 'Housing' },
    { 'question': 'मालमत्ता कर ऑनलाइन कसा भरायचा?', 'answer': 'मालमत्ता कर आपल्या नगर महापालिकेच्या वेबसाइटवर भरा. मालमत्ता मूल्यांकन क्रमांक आवश्यक आहे. UPI, नेट बँकिंग आणि कार्ड पेमेंट स्वीकारले जाते.', 'language': 'mr', 'category': 'Housing' },
    { 'question': 'जन धन खाते कसे उघडायचे?', 'answer': 'कोणत्याही राष्ट्रीयीकृत बँकेत किंवा टपाल कार्यालयात आधार आणि पासपोर्ट फोटोसह PMJDY खाते उघडा. किमान शिल्लक नाही. RuPay डेबिट कार्ड आणि २ लाख रुपयांचा अपघात विमा मिळतो.', 'language': 'mr', 'category': 'Finance' },
    { 'question': 'मुद्रा कर्जासाठी अर्ज कसा करायचा?', 'answer': 'कोणत्याही बँक, MFI किंवा NBFC मध्ये PMMY मुद्रा कर्जासाठी अर्ज करा. कोणतीही हमी नाही. तीन श्रेण्या: शिशु (५०,००० पर्यंत), किशोर (५ लाखांपर्यंत), तरुण (१० लाखांपर्यंत).', 'language': 'mr', 'category': 'Finance' },
    { 'question': 'सरकारी कार्यालयाविरुद्ध तक्रार कशी करायची?', 'answer': 'pgportal.gov.in वर ऑनलाइन तक्रार करा. CM हेल्पलाइनसाठी आपल्या राज्याचा नंबर डायल करा. RTI अर्ज rtionline.gov.in वर दाखल करा.', 'language': 'mr', 'category': 'Grievance' },
]
