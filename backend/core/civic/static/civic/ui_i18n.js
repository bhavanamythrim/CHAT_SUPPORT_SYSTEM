/* Global UI translation helper (client-side, exact text match) */
(function () {
  const lang =
    (document.documentElement && document.documentElement.dataset.uiLang) || "en";

  if (!lang || lang === "en") return;

  const UI_TRANSLATIONS = {
    ta: {
      "Smart Civic HelpDesk": "ஸ்மார்ட் சிவிக் ஹெல்ப்டெஸ்க்",
      "+ New Conversation": "+ புதிய உரையாடல்",
      "New Conversation": "புதிய உரையாடல்",
      "Recent Sessions": "சமீபத்திய அமர்வுகள்",
      "No recent chats.": "சமீபத்திய உரையாடல்கள் இல்லை.",
      Chat: "அரட்டை",
      Profile: "சுயவிவரம்",
      Complaints: "புகார்கள்",
      Documents: "ஆவணங்கள்",
      Settings: "அமைப்புகள்",
      "Agent Panel": "ஏஜென்ட் பகுதி",
      Admin: "நிர்வாகம்",
      Logout: "வெளியேறு",
      Login: "உள்நுழை",
      Register: "பதிவு",
      Notifications: "அறிவிப்புகள்",
      "Mark all read": "அனைத்தையும் படித்ததாக குறி",
      "No new alerts.": "புதிய அறிவிப்புகள் இல்லை.",
      "Start chatting for support.": "உதவிக்காக உரையாடலைத் தொடங்குங்கள்.",
      "Nearby Offices": "அருகிலுள்ள அலுவலகங்கள்",
      "Click location pin to detect your location":
        "உங்கள் இருப்பிடத்தை அறிய இடம் குறியை கிளிக் செய்யவும்",
      "Click 📍 to detect your location":
        "உங்கள் இருப்பிடத்தை அறிய 📍 கிளிக் செய்யவும்",
      Escalation: "மேம்படுத்தல்",
      "Need human help for unresolved issues.":
        "தீராத பிரச்சினைகளுக்கு மனித உதவி தேவை.",
      "Escalate Complaint": "புகாரை உயர்த்தவும்",
      "AI Summary": "ஏஐ சுருக்கம்",
      TOPIC: "தலைப்பு",
      "General civic support": "பொது குடிமக்கள் ஆதரவு",
      QUICK: "விரைவு",
      "Pay EB Bill": "EB கட்டணம் செலுத்த",
      "Post Office Nearby": "அருகிலுள்ள தபால் நிலையம்",
      "Report Pothole": "சாலை குழி புகார்",
      "Birth Certificate": "பிறப்பு சான்றிதழ்",
      "Health Camp Info": "சுகாதார முகாம் தகவல்",
      "Aadhaar Update": "ஆதார் புதுப்பிப்பு",
      "Ask about any civic service, complaint, or nearby office...":
        "எந்த அரசுப் பணிகள், புகார், அல்லது அருகிலுள்ள அலுவலகம் குறித்து கேளுங்கள்...",
      "Enter to send, Shift+Enter for new line":
        "அனுப்ப Enter, புதிய வரிக்க Shift+Enter",
      "No nearby office loaded yet.": "அருகிலுள்ள அலுவலகங்கள் இன்னும் ஏற்றப்படவில்லை."
    },
    hi: {
      "Smart Civic HelpDesk": "स्मार्ट सिविक हेल्पडेस्क",
      "+ New Conversation": "+ नई बातचीत",
      "New Conversation": "नई बातचीत",
      "Recent Sessions": "हाल की सत्र",
      "No recent chats.": "कोई हाल की चैट नहीं।",
      Chat: "चैट",
      Profile: "प्रोफाइल",
      Complaints: "शिकायतें",
      Documents: "दस्तावेज़",
      Settings: "सेटिंग्स",
      "Agent Panel": "एजेंट पैनल",
      Admin: "एडमिन",
      Logout: "लॉगआउट",
      Login: "लॉगिन",
      Register: "रजिस्टर",
      Notifications: "सूचनाएं",
      "Mark all read": "सभी पढ़ा हुआ चिह्नित करें",
      "No new alerts.": "कोई नई सूचना नहीं।",
      "Start chatting for support.": "सहायता के लिए चैट शुरू करें।",
      "Nearby Offices": "नजदीकी कार्यालय",
      "Click location pin to detect your location":
        "अपना स्थान जानने के लिए लोकेशन पिन पर क्लिक करें",
      "Click 📍 to detect your location":
        "अपना स्थान जानने के लिए 📍 पर क्लिक करें",
      Escalation: "एस्केलेशन",
      "Need human help for unresolved issues.":
        "अपूर्ण समस्याओं के लिए मानव सहायता चाहिए।",
      "Escalate Complaint": "शिकायत बढ़ाएं",
      "AI Summary": "एआई सारांश",
      TOPIC: "विषय",
      "General civic support": "सामान्य नागरिक सहायता",
      QUICK: "त्वरित",
      "Pay EB Bill": "EB बिल भुगतान",
      "Post Office Nearby": "नजदीकी डाकघर",
      "Report Pothole": "गड्ढे की शिकायत",
      "Birth Certificate": "जन्म प्रमाण पत्र",
      "Health Camp Info": "स्वास्थ्य शिविर जानकारी",
      "Aadhaar Update": "आधार अपडेट",
      "Ask about any civic service, complaint, or nearby office...":
        "किसी भी नागरिक सेवा, शिकायत या नजदीकी कार्यालय के बारे में पूछें...",
      "Enter to send, Shift+Enter for new line":
        "भेजने के लिए Enter, नई लाइन के लिए Shift+Enter",
      "No nearby office loaded yet.": "अभी कोई नजदीकी कार्यालय लोड नहीं हुआ।"
    },
    te: {
      "Smart Civic HelpDesk": "స్మార్ట్ సివిక్ హెల్ప్‌డెస్క్",
      "+ New Conversation": "+ కొత్త సంభాషణ",
      "New Conversation": "కొత్త సంభాషణ",
      "Recent Sessions": "ఇటీవలి సెషన్లు",
      "No recent chats.": "ఇటీవలి చాట్లు లేవు.",
      Chat: "చాట్",
      Profile: "ప్రొఫైల్",
      Complaints: "ఫిర్యాదులు",
      Documents: "పత్రాలు",
      Settings: "సెట్టింగ్స్",
      "Agent Panel": "ఏజెంట్ ప్యానెల్",
      Admin: "అడ్మిన్",
      Logout: "లాగౌట్",
      Login: "లాగిన్",
      Register: "రిజిస్టర్",
      Notifications: "నోటిఫికేషన్లు",
      "Mark all read": "అన్నీ చదివినట్లు గుర్తించండి",
      "No new alerts.": "కొత్త అలర్ట్స్ లేవు.",
      "Start chatting for support.": "సహాయానికి చాటింగ్ ప్రారంభించండి.",
      "Nearby Offices": "సమీప కార్యాలయాలు",
      "Click location pin to detect your location":
        "మీ స్థానం గుర్తించేందుకు లొకేషన్ పిన్ క్లిక్ చేయండి",
      "Click 📍 to detect your location":
        "మీ స్థానం కోసం 📍 క్లిక్ చేయండి",
      Escalation: "ఎస్కలేషన్",
      "Need human help for unresolved issues.":
        "పరిష్కారం కాని సమస్యలకు మానవ సహాయం కావాలి.",
      "Escalate Complaint": "ఫిర్యాదు ఎస్కలేట్ చేయండి",
      "AI Summary": "AI సారాంశం",
      TOPIC: "విషయం",
      "General civic support": "సాధారణ పౌర సహాయం",
      QUICK: "త్వరిత",
      "Pay EB Bill": "EB బిల్ చెల్లింపు",
      "Post Office Nearby": "సమీప పోస్టాఫీస్",
      "Report Pothole": "గోతు ఫిర్యాదు",
      "Birth Certificate": "జనన సర్టిఫికేట్",
      "Health Camp Info": "హెల్త్ క్యాంప్ సమాచారం",
      "Aadhaar Update": "ఆధార్ అప్‌డేట్",
      "Ask about any civic service, complaint, or nearby office...":
        "ఏ సేవ, ఫిర్యాదు, లేదా సమీప కార్యాలయం గురించి అడగండి...",
      "Enter to send, Shift+Enter for new line":
        "పంపేందుకు Enter, కొత్త లైన్ కోసం Shift+Enter",
      "No nearby office loaded yet.": "సమీప కార్యాలయాలు ఇంకా లోడ్ కాలేదు."
    },
    ml: {
      "Smart Civic HelpDesk": "സ്മാർട്ട് സിവിക് ഹെൽപ്‌ഡെസ്ക്",
      "+ New Conversation": "+ പുതിയ സംഭാഷണം",
      "New Conversation": "പുതിയ സംഭാഷണം",
      "Recent Sessions": "സമീപകാല സെഷനുകൾ",
      "No recent chats.": "സമീപകാല ചാറ്റുകൾ ഇല്ല.",
      Chat: "ചാറ്റ്",
      Profile: "പ്രൊഫൈൽ",
      Complaints: "പരാതികൾ",
      Documents: "രേഖകൾ",
      Settings: "ക്രമീകരണങ്ങൾ",
      "Agent Panel": "ഏജന്റ് പാനൽ",
      Admin: "അഡ്മിൻ",
      Logout: "ലോഗൗട്ട്",
      Login: "ലോഗിൻ",
      Register: "രജിസ്റ്റർ",
      Notifications: "അറിയിപ്പുകൾ",
      "Mark all read": "എല്ലാം വായിച്ചതായി അടയാളപ്പെടുത്തുക",
      "No new alerts.": "പുതിയ അറിയിപ്പുകൾ ഇല്ല.",
      "Start chatting for support.": "സഹായത്തിനായി ചാറ്റ് ആരംഭിക്കുക.",
      "Nearby Offices": "സമീപ ഓഫീസുകൾ",
      "Click location pin to detect your location":
        "നിങ്ങളുടെ സ്ഥാനം കണ്ടെത്താൻ ലൊക്കേഷൻ പിൻ ക്ലിക്കുചെയ്യുക",
      "Click 📍 to detect your location":
        "നിങ്ങളുടെ സ്ഥാനം കണ്ടെത്താൻ 📍 ക്ലിക്കുചെയ്യുക",
      Escalation: "എസ്കലേഷൻ",
      "Need human help for unresolved issues.":
        "പരിഹരിക്കാത്ത പ്രശ്‌നങ്ങൾക്ക് മനുഷ്യ സഹായം ആവശ്യമാണ്.",
      "Escalate Complaint": "പരാതി ഉയർത്തുക",
      "AI Summary": "AI സംക്ഷേപം",
      TOPIC: "വിഷയം",
      "General civic support": "പൊതുവായ സിവിക് പിന്തുണ",
      QUICK: "വേഗം",
      "Pay EB Bill": "EB ബിൽ പേയ് ചെയ്യുക",
      "Post Office Nearby": "സമീപ പോസ്റ്റോഫീസ്",
      "Report Pothole": "കുഴി പരാതി",
      "Birth Certificate": "ജനന സർട്ടിഫിക്കറ്റ്",
      "Health Camp Info": "ആരോഗ്യ ക്യാമ്പ് വിവരങ്ങൾ",
      "Aadhaar Update": "ആധാർ അപ്ഡേറ്റ്",
      "Ask about any civic service, complaint, or nearby office...":
        "ഏതെങ്കിലും സിവിക് സേവനം, പരാതി, അല്ലെങ്കിൽ സമീപ ഓഫീസ് ചോദിക്കുക...",
      "Enter to send, Shift+Enter for new line":
        "അയക്കാൻ Enter, പുതിയ വരിക്ക് Shift+Enter",
      "No nearby office loaded yet.": "സമീപ ഓഫീസുകൾ ഇതുവരെ ലോഡ് ചെയ്തിട്ടില്ല."
    },
    kn: {
      "Smart Civic HelpDesk": "ಸ್ಮಾರ್ಟ್ ಸಿವಿಕ್ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್",
      "+ New Conversation": "+ ಹೊಸ ಸಂಭಾಷಣೆ",
      "New Conversation": "ಹೊಸ ಸಂಭಾಷಣೆ",
      "Recent Sessions": "ಇತ್ತೀಚಿನ ಸೆಷನ್‌ಗಳು",
      "No recent chats.": "ಇತ್ತೀಚಿನ ಚಾಟ್‌ಗಳಿಲ್ಲ.",
      Chat: "ಚಾಟ್",
      Profile: "ಪ್ರೊಫೈಲ್",
      Complaints: "ದೂರುಗಳು",
      Documents: "ದಸ್ತಾವೇಜುಗಳು",
      Settings: "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
      "Agent Panel": "ಏಜೆಂಟ್ ಪ್ಯಾನೆಲ್",
      Admin: "ಆಡ್ಮಿನ್",
      Logout: "ಲಾಗ್ಔಟ್",
      Login: "ಲಾಗಿನ್",
      Register: "ರಿಜಿಸ್ಟರ್",
      Notifications: "ಅಧಿಸೂಚನೆಗಳು",
      "Mark all read": "ಎಲ್ಲವೂ ಓದಿದಂತೆ ಗುರುತುಮಾಡಿ",
      "No new alerts.": "ಹೊಸ ಅಲರ್ಟ್‌ಗಳಿಲ್ಲ.",
      "Start chatting for support.": "ಸಹಾಯಕ್ಕಾಗಿ ಚಾಟ್ ಪ್ರಾರಂಭಿಸಿ.",
      "Nearby Offices": "ಹತ್ತಿರದ ಕಚೇರಿಗಳು",
      "Click location pin to detect your location":
        "ನಿಮ್ಮ ಸ್ಥಳ ತಿಳಿಯಲು ಲೊಕೇಷನ್ ಪಿನ್ ಕ್ಲಿಕ್ ಮಾಡಿ",
      "Click 📍 to detect your location":
        "ನಿಮ್ಮ ಸ್ಥಳಕ್ಕಾಗಿ 📍 ಕ್ಲಿಕ್ ಮಾಡಿ",
      Escalation: "ಏರಿಕೆ",
      "Need human help for unresolved issues.":
        "ಪರಿಹಾರವಾಗದ ಸಮಸ್ಯೆಗಳಿಗೆ ಮಾನವ ಸಹಾಯ ಬೇಕು.",
      "Escalate Complaint": "ದೂರು ಎಸ್ಕಲೇಟ್ ಮಾಡಿ",
      "AI Summary": "AI ಸಾರಾಂಶ",
      TOPIC: "ವಿಷಯ",
      "General civic support": "ಸಾಮಾನ್ಯ ನಾಗರಿಕ ನೆರವು",
      QUICK: "ತ್ವರಿತ",
      "Pay EB Bill": "EB ಬಿಲ್ ಪಾವತಿ",
      "Post Office Nearby": "ಹತ್ತಿರದ ಅಂಚೆ ಕಚೇರಿ",
      "Report Pothole": "ಗದ್ದೆ ದೂರು",
      "Birth Certificate": "ಜನನ ಪ್ರಮಾಣಪತ್ರ",
      "Health Camp Info": "ಆರೋಗ್ಯ ಶಿಬಿರ ಮಾಹಿತಿ",
      "Aadhaar Update": "ಆಧಾರ್ ಅಪ್ಡೇಟ್",
      "Ask about any civic service, complaint, or nearby office...":
        "ಯಾವುದೇ ಸೇವೆ, ದೂರು ಅಥವಾ ಹತ್ತಿರದ ಕಚೇರಿ ಕುರಿತು ಕೇಳಿ...",
      "Enter to send, Shift+Enter for new line":
        "ಕಳಿಸಲು Enter, ಹೊಸ ಸಾಲಿಗೆ Shift+Enter",
      "No nearby office loaded yet.": "ಹತ್ತಿರದ ಕಚೇರಿಗಳು ಇನ್ನೂ ಲೋಡ್ ಆಗಿಲ್ಲ."
    },
    mr: {
      "Smart Civic HelpDesk": "स्मार्ट सिविक हेल्पडेस्क",
      "+ New Conversation": "+ नवीन संभाषण",
      "New Conversation": "नवीन संभाषण",
      "Recent Sessions": "अलीकडील सत्रे",
      "No recent chats.": "अलीकडील चॅट्स नाहीत.",
      Chat: "चॅट",
      Profile: "प्रोफाइल",
      Complaints: "तक्रारी",
      Documents: "दस्तऐवज",
      Settings: "सेटिंग्स",
      "Agent Panel": "एजंट पॅनल",
      Admin: "ॲडमिन",
      Logout: "लॉगआउट",
      Login: "लॉगिन",
      Register: "नोंदणी",
      Notifications: "सूचना",
      "Mark all read": "सर्व वाचलेले म्हणून चिन्हांकित करा",
      "No new alerts.": "नवीन सूचना नाहीत.",
      "Start chatting for support.": "मदतीसाठी चॅट सुरू करा.",
      "Nearby Offices": "जवळची कार्यालये",
      "Click location pin to detect your location":
        "तुमचे स्थान शोधण्यासाठी लोकेशन पिन क्लिक करा",
      "Click 📍 to detect your location":
        "तुमचे स्थानासाठी 📍 क्लिक करा",
      Escalation: "एस्कलेशन",
      "Need human help for unresolved issues.":
        "निराकरण न झालेल्या समस्यांसाठी मानवी मदत हवी आहे.",
      "Escalate Complaint": "तक्रार वाढवा",
      "AI Summary": "AI सारांश",
      TOPIC: "विषय",
      "General civic support": "सामान्य नागरी सहाय्य",
      QUICK: "जलद",
      "Pay EB Bill": "EB बिल भरा",
      "Post Office Nearby": "जवळचे टपाल कार्यालय",
      "Report Pothole": "खड्ड्याची तक्रार",
      "Birth Certificate": "जन्म प्रमाणपत्र",
      "Health Camp Info": "आरोग्य शिबिर माहिती",
      "Aadhaar Update": "आधार अपडेट",
      "Ask about any civic service, complaint, or nearby office...":
        "कोणत्याही सेवा, तक्रार किंवा जवळच्या कार्यालयाबद्दल विचारा...",
      "Enter to send, Shift+Enter for new line":
        "पाठवण्यासाठी Enter, नवीन ओळीसाठी Shift+Enter",
      "No nearby office loaded yet.": "जवळची कार्यालये अद्याप लोड झालेली नाहीत."
    },
    bn: {
      "Smart Civic HelpDesk": "স্মার্ট সিভিক হেল্পডেস্ক",
      "+ New Conversation": "+ নতুন কথোপকথন",
      "New Conversation": "নতুন কথোপকথন",
      "Recent Sessions": "সাম্প্রতিক সেশন",
      "No recent chats.": "কোনও সাম্প্রতিক চ্যাট নেই।",
      Chat: "চ্যাট",
      Profile: "প্রোফাইল",
      Complaints: "অভিযোগ",
      Documents: "নথি",
      Settings: "সেটিংস",
      "Agent Panel": "এজেন্ট প্যানেল",
      Admin: "অ্যাডমিন",
      Logout: "লগআউট",
      Login: "লগইন",
      Register: "রেজিস্টার",
      Notifications: "নোটিফিকেশন",
      "Mark all read": "সব পড়া হয়েছে হিসেবে চিহ্নিত করুন",
      "No new alerts.": "কোনও নতুন সতর্কতা নেই।",
      "Start chatting for support.": "সহায়তার জন্য চ্যাট শুরু করুন।",
      "Nearby Offices": "কাছাকাছি অফিস",
      "Click location pin to detect your location":
        "আপনার অবস্থান জানতে লোকেশন পিন ক্লিক করুন",
      "Click 📍 to detect your location":
        "আপনার অবস্থান জানতে 📍 ক্লিক করুন",
      Escalation: "এস্কেলেশন",
      "Need human help for unresolved issues.":
        "অসমাধানযোগ্য সমস্যার জন্য মানব সহায়তা প্রয়োজন।",
      "Escalate Complaint": "অভিযোগ উন্নীত করুন",
      "AI Summary": "AI সারাংশ",
      TOPIC: "বিষয়",
      "General civic support": "সাধারণ নাগরিক সহায়তা",
      QUICK: "দ্রুত",
      "Pay EB Bill": "EB বিল পরিশোধ",
      "Post Office Nearby": "কাছাকাছি পোস্ট অফিস",
      "Report Pothole": "গর্তের অভিযোগ",
      "Birth Certificate": "জন্ম সনদ",
      "Health Camp Info": "স্বাস্থ্য শিবির তথ্য",
      "Aadhaar Update": "আধার আপডেট",
      "Ask about any civic service, complaint, or nearby office...":
        "যে কোনও সিভিক সেবা, অভিযোগ বা কাছাকাছি অফিস সম্পর্কে জিজ্ঞাসা করুন...",
      "Enter to send, Shift+Enter for new line":
        "পাঠাতে Enter, নতুন লাইনে Shift+Enter",
      "No nearby office loaded yet.": "এখনও কোনও কাছাকাছি অফিস লোড হয়নি।"
    }
  };

  function translateText(text) {
    const map = UI_TRANSLATIONS[lang];
    if (!map) return text;
    return map[text] || text;
  }

  function translateElement(el) {
    if (!el) return;
    const hasChildren = el.children && el.children.length > 0;
    const key = el.getAttribute("data-i18n-key");

    if (key) {
      el.textContent = translateText(key);
      return;
    }

    if (!hasChildren) {
      const raw = (el.textContent || "").trim();
      if (raw) {
        const translated = translateText(raw);
        if (translated !== raw) {
          el.textContent = translated;
        }
      }
    }

    if (el.placeholder) {
      el.placeholder = translateText(el.placeholder);
    }

    if (el.title) {
      el.title = translateText(el.title);
    }

    if (el.getAttribute("aria-label")) {
      el.setAttribute("aria-label", translateText(el.getAttribute("aria-label")));
    }
  }

  function applyUiTranslations() {
    const all = document.querySelectorAll("body *");
    all.forEach(translateElement);
  }

  window.applyUiTranslations = applyUiTranslations;
  document.addEventListener("DOMContentLoaded", applyUiTranslations);
})();
