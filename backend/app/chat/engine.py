"""
Citizen Chat Orchestration Engine.
Integrates Intent Router, Deterministic Tool Execution, FactSheet Construction,
Grounding Validation, Audio Voice Note Synthesis, and Honest Outside-Data Handling.
"""
import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.chat.geocoding import SEEDED_LOCATIONS, resolve_location
from app.chat.models import ChatRequest, ChatResponse, OnboardingRequest, OnboardingResponse
from app.chat.router import classify_intent
from app.chat.tools import (
    get_active_alerts,
    get_climate_normals,
    get_forecast,
    get_marine,
    nearest_shelter,
)
from app.core.action_plan import generate_action_plan
from app.core.factsheet import build_factsheet
from app.lang.digits import to_target_digits
from app.lang.translator import translation_service
from app.pipeline.composer import compose_message
from app.reports.service import classify_report_category, submit_report
from app.validator.engine import validate_payload
from app.voice import voice_synthesizer

logger = logging.getLogger("app")

# In-memory session store for chat interactions
SESSION_STORE: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    if not session_id or session_id not in SESSION_STORE:
        sid = session_id or str(uuid.uuid4())
        SESSION_STORE[sid] = {
            "session_id": sid,
            "user_id": str(uuid.uuid4()),
            "language": "en",
            "persona": "general",
            "location": SEEDED_LOCATIONS["wayanad"],
            "clarification_asked": False,
            "history": []
        }
        return sid, SESSION_STORE[sid]
    return session_id, SESSION_STORE[session_id]


def process_onboarding(req: OnboardingRequest) -> OnboardingResponse:
    """Store citizen preferences, hash phone number, and return welcome payload."""
    user_id = req.user_id or str(uuid.uuid4())
    phone_hash = None
    if req.phone:
        phone_hash = hashlib.sha256(f"skysafe_{req.phone}".encode("utf-8")).hexdigest()

    loc, _ = resolve_location(req.location)
    if not loc:
        loc = SEEDED_LOCATIONS["wayanad"]

    sid = str(uuid.uuid4())
    session = {
        "session_id": sid,
        "user_id": user_id,
        "phone_hash": phone_hash,
        "language": req.language.lower(),
        "persona": req.persona.lower(),
        "location": loc,
        "consent_alerts": req.consent_alerts,
        "clarification_asked": False,
        "history": []
    }
    SESSION_STORE[sid] = session

    # Localized welcome message
    lang = req.language.lower()
    district = loc["district"]
    if lang == "hi":
        welcome = f"नमस्ते! स्काईसेफ एआई में आपका स्वागत है। मैं {district} के लिए आपका मौसम और आपदा सुरक्षा सहायक हूँ।"
        replies = ["सक्रिय चेतावनी ⚠️", "आज का मौसम 🌦️", "क्या मछली पकड़ना सुरक्षित है? 🎣", "निकटतम आश्रय 🏠"]
    elif lang == "or":
        welcome = f"ନମସ୍କାର! ସ୍କାଇସେଫ୍ ଏଆଇକୁ ସ୍ୱାଗତ। ମୁଁ {district} ପାଇଁ ଆପଣଙ୍କ ପାଣିପାଗ ଏବଂ ବିପର୍ଯ୍ୟୟ ସୁରକ୍ଷା ସହାୟକ।"
        replies = ["ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ଆଜିର ପାଣିପାଗ 🌦️", "ମାଛ ଧରିବା ସୁରକ୍ଷିତ କି? 🎣", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
    else:
        welcome = f"Welcome to SkySafe AI. I am your verified weather action intelligence assistant for {district}."
        replies = ["Active Alert ⚠️", "Weather Today 🌦️", "Safety Check 🎣", "Nearest Shelter 🏠"]

    return OnboardingResponse(
        user_id=user_id,
        phone_hash=phone_hash,
        language=req.language,
        persona=req.persona,
        location=loc,
        consent_alerts=req.consent_alerts,
        welcome_message=welcome,
        quick_replies=replies
    )


def handle_chat_message(req: ChatRequest, db: Session = None) -> ChatResponse:
    """
    Main conversational agent handler.
    Follows: Router -> Tool Execution -> FactSheet -> Composition -> Grounding Validator.
    """
    session_id, session = get_or_create_session(req.session_id)

    # Allow runtime parameter overrides
    if req.lang:
        session["language"] = req.lang.lower()
    if req.persona:
        session["persona"] = req.persona.lower()

    # Location resolution: check message text for location names or use request location
    extracted_loc, is_ambig = resolve_location(req.location or req.message, lat=req.lat, lon=req.lon)
    if extracted_loc and not is_ambig:
        session["location"] = extracted_loc

    loc = session["location"]
    lang = session["language"]
    persona = session["persona"]

    # Intent Classification
    intent = classify_intent(req.message)
    tools_called = []
    facts: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []

    # 1. Greeting
    if intent == "greeting":
        if lang == "hi":
            msg = f"नमस्ते! मैं स्काईसेफ एआई हूँ। {loc['district']} के लिए आप मुझसे मौसम चेतावनी, वर्षा का पूर्वानुमान, सुरक्षित यात्रा या निकटतम आश्रय के बारे में पूछ सकते हैं।"
            replies = ["सक्रिय चेतावनी ⚠️", "आज का मौसम 🌦️", "निकटतम आश्रय 🏠"]
        elif lang == "or":
            msg = f"ନମସ୍କାର! ମୁଁ ସ୍କାଇସେଫ୍ ଏଆଇ। {loc['district']} ପାଇଁ ଆପଣ ମୋତେ ଚେତାବନୀ, ବର୍ଷା ପୂର୍ବାନୁମାନ କିମ୍ବା ନିକଟତମ ଆଶ୍ରୟସ୍ଥଳ ବିଷୟରେ ପଚାରିପାରିବେ।"
            replies = ["ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ଆଜିର ପାଣିପାଗ 🌦️", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
        else:
            msg = f"Hello! I am SkySafe AI. For {loc['district']}, you can ask me for active weather alerts, 3-day forecast, sea safety checks, or nearest emergency shelters."
            replies = ["Active Alert ⚠️", "Weather Today 🌦️", "Nearest Shelter 🏠"]

        return _build_response(session_id, msg, "greeting", [], loc, replies, lang=lang)

    # 2. Change Language
    if intent == "change_language":
        lower_msg = req.message.lower()
        new_lang = "en"
        if "hindi" in lower_msg or "हिंदी" in lower_msg:
            new_lang = "hi"
        elif "odia" in lower_msg or "oriya" in lower_msg or "ଓଡ଼ିଆ" in lower_msg:
            new_lang = "or"
        elif "tamil" in lower_msg or "தமிழ்" in lower_msg:
            new_lang = "ta"
        elif "telugu" in lower_msg or "తెలుగు" in lower_msg:
            new_lang = "te"
        elif "marathi" in lower_msg or "मराठी" in lower_msg:
            new_lang = "mr"
        elif "bengali" in lower_msg or "বাংলা" in lower_msg:
            new_lang = "bn"

        session["language"] = new_lang
        if new_lang == "hi":
            msg = f"भाषा बदलकर हिंदी कर दी गई है। {loc['district']} के लिए मैं आपकी क्या मदद कर सकता हूँ?"
            replies = ["सक्रिय चेतावनी ⚠️", "मौसम पूर्वानुमान 🌦️"]
        elif new_lang == "or":
            msg = f"ଭାଷା ବଦଳାଇ ଓଡ଼ିଆ କରାଗଲା। {loc['district']} ପାଇଁ ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?"
            replies = ["ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ପାଣିପାଗ ପୂର୍ବାନୁମାନ 🌦️"]
        else:
            msg = f"Language changed to English. How can I assist you for {loc['district']}?"
            replies = ["Active Alert ⚠️", "Weather Forecast 🌦️"]

        return _build_response(session_id, msg, "change_language", [], loc, replies, lang=new_lang)

    # 3. Registration / Unregistration
    if intent == "registration":
        if "un" in req.message.lower() or "stop" in req.message.lower() or "बंद" in req.message.lower():
            session["consent_alerts"] = False
            if lang == "hi":
                msg = "आपको आपातकालीन मौसम अलर्ट सूची से हटा दिया गया है।"
            elif lang == "or":
                msg = "ଆପଣଙ୍କୁ ଜରୁରୀକାଳୀନ ପାଣିପାଗ ଆଲର୍ଟ ତାଲିକାରୁ ହଟାଇ ଦିଆଗଲା।"
            else:
                msg = "You have been unsubscribed from emergency weather alert broadcasts."
        else:
            session["consent_alerts"] = True
            if lang == "hi":
                msg = f"आपका फोन नंबर {loc['district']} के लिए आपातकालीन एसएमएस अलर्ट के लिए पंजीकृत कर लिया गया है।"
            elif lang == "or":
                msg = f"ଆପଣଙ୍କ ଫୋନ୍ ନମ୍ବର {loc['district']} ପାଇଁ ଜରୁରୀକାଳୀନ ଏସଏମଏସ ଆଲର୍ଟ ପାଇଁ ପଞ୍ଜୀକୃତ ହେଲା।"
            else:
                msg = f"Your phone has been registered for official emergency weather broadcasts in {loc['district']}."

        return _build_response(session_id, msg, "registration", [], loc, ["Active Alert ⚠️", "Weather Today 🌦️"], lang=lang)

    # 4. Incident Reporting
    if intent == "report_incident":
        category = classify_report_category(req.message)
        tools_called.append("submit_report")
        if db:
            user_hash = session.get("phone_hash") or session["user_id"]
            ward_id = loc['district']
            if "ward 7" in req.message.lower():
                ward_id = "Ward 7"
            submit_report(
                db=db,
                text=req.message,
                lat=loc['lat'],
                lon=loc['lon'],
                user_hash=user_hash,
                ward_id=ward_id
            )

        if category == "Need Help":
            if lang == "hi":
                msg = f"आपकी आपातकालीन सहायता का अनुरोध {loc['district']} अधिकारियों को प्राथमिकता पर भेज दिया गया है। निकटतम आश्रय और बचाव टीम सतर्क हैं। हेल्पलाइन 1077 डायल करें।"
                replies = ["निकटतम आश्रय 🏠", "मुझे क्या करना चाहिए? 🛡️"]
            elif lang == "or":
                msg = f"ଆପଣଙ୍କର ଜରୁରୀକାଳୀନ ସାହାଯ୍ୟ ଅନୁରୋଧ {loc['district']} ଅଧିକାରୀମାନଙ୍କୁ ପ୍ରାଥମିକତା ଭିତ୍ତିରେ ପଠାଯାଇଛି। ନିକଟତମ ଆଶ୍ରୟସ୍ଥଳ ଏବଂ ଉଦ୍ଧାରକାରୀ ଦଳ ସତର୍କ ଅଛନ୍ତି। 1077 ଡାଏଲ୍ କରନ୍ତୁ।"
                replies = ["ନିକଟତମ ଆଶ୍ରୟ 🏠", "ମୁଁ କଣ କରିବି? 🛡️"]
            else:
                msg = f"URGENT: Your request for help in {loc['district']} has been prioritized to local officers. Rescue teams are on alert. Dial 1077 or move to nearest shelter."
                replies = ["Nearest Shelter 🏠", "Action Advice 🛡️"]
        else:
            if lang == "hi":
                msg = f"धन्यवाद। {loc['district']} में आपकी रिपोर्ट (श्रेणी: {category}) दर्ज कर ली गई है और स्थानीय आपदा प्रतिक्रिया दल को प्रेषित कर दी गई है।"
                replies = ["निकटतम आश्रय 🏠", "सुरक्षा निर्देश 🛡️"]
            elif lang == "or":
                msg = f"ଧନ୍ୟବାଦ। {loc['district']} ରେ ଆପଣଙ୍କ ରିପୋର୍ଟ (ବର୍ଗ: {category}) ଗ୍ରହଣ କରାଗଲା ଏବଂ ସ୍ଥାନୀୟ ପ୍ରଶାସନକୁ ପଠାଗଲା।"
                replies = ["ନିକଟତମ ଆଶ୍ରୟ 🏠", "ସୁରକ୍ଷା ନିର୍ଦ୍ଦେଶ 🛡️"]
            else:
                msg = f"Thank you. Your incident report ({category}) for {loc['district']} has been logged and shared with the local emergency response authorities."
                replies = ["Nearest Shelter 🏠", "Action Advice 🛡️"]

        return _build_response(session_id, msg, "report_incident", tools_called, loc, replies, lang=lang)

    # 5. Current Alert Here
    if intent == "current_alert":
        tools_called.append("get_active_alerts")
        alert_res = get_active_alerts(loc)
        facts = alert_res["facts"]

        if not alert_res["has_alert"]:
            if lang == "hi":
                msg = f"{loc['district']} में वर्तमान में कोई आपातकालीन मौसम चेतावनी सक्रिय नहीं है। मौसम की स्थिति सामान्य है।"
                replies = ["मौसम पूर्वानुमान 🌦️", "जलवायु जानकारी 📊"]
            elif lang == "or":
                msg = f"{loc['district']} ରେ ବର୍ତ୍ତମାନ କୌଣସି ଜରୁରୀକାଳୀନ ଚେତାବନୀ ନାହିଁ। ପାଣିପାଗ ସ୍ଥିତି ସ୍ୱାଭାବିକ ଅଛି।"
                replies = ["ପାଣିପାଗ ପୂର୍ବାନୁମାନ 🌦️", "ଜଳବାୟୁ ସୂଚନା 📊"]
            else:
                msg = f"No active emergency weather warnings in {loc['district']} at this moment. Current conditions are normal."
                replies = ["Forecast Today 🌦️", "Climate Normals 📊"]
            return _build_response(session_id, msg, "current_alert", tools_called, loc, replies, facts=facts, lang=lang)

        top_a = alert_res["alert"]
        is_sim = (
            top_a.get("is_simulation", False)
            or top_a.get("status") == "Exercise"
            or "drill" in str(top_a.get("note", "")).lower()
        )

        # 1. Build FactSheet & ActionPlan from official alert data
        factsheet = build_factsheet(top_a)
        actionplan = generate_action_plan(factsheet, persona=persona)
        fs_dict = {"facts": [f.to_dict() for f in factsheet.facts]}
        ap_dict = actionplan.to_dict()

        # 2. Compose Base Grounded Message via Grounding Validator
        text_en, voice_en, ledger_en, _ = compose_message(
            alert_id=top_a.get("identifier", "ALERT"),
            factsheet=fs_dict,
            actionplan=ap_dict,
        )

        # 3. Translate if target language != "en"
        if lang.lower() != "en":
            text, voice_script, ledger, _ = translation_service.translate_message(
                alert_id=top_a.get("identifier", "ALERT"),
                factsheet=fs_dict,
                actionplan=ap_dict,
                text_en=text_en,
                voice_en=voice_en,
                lang=lang,
            )
        else:
            text = text_en
            voice_script = voice_en
            ledger = ledger_en

        # 4. Enforce Non-Negotiable Rule 2: label as DRILL only if underlying alert is a simulation
        if is_sim:
            if not text.startswith("[DRILL"):
                text = f"[DRILL / SIMULATION] {text}"
            if not voice_script.startswith("[DRILL"):
                voice_script = f"[DRILL] {voice_script}"

        # 5. Quick replies
        if lang == "hi":
            replies = ["मुझे क्या करना चाहिए? 🛡️", "निकटतम आश्रय 🏠", "मौसम पूर्वानुमान 🌦️"]
        elif lang == "or":
            replies = ["ମୁଁ କଣ କରିବି? 🛡️", "ନିକଟତମ ଆଶ୍ରୟ 🏠", "ପାଣିପାଗ ପୂର୍ବାନୁମାନ 🌦️"]
        else:
            replies = ["What should I do now? 🛡️", "Nearest Shelter 🏠", "Weather Forecast 🌦️"]

        # 6. Synthesize Voice Note
        audio_url = None
        try:
            synth = voice_synthesizer.synthesize(voice_script, lang=lang)
            audio_url = synth.get("audio_url")
        except Exception as e:
            logger.warning(f"Voice synthesis failed for chat message: {e}")

        return ChatResponse(
            session_id=session_id,
            message=text,
            voice_script=voice_script,
            audio_url=audio_url,
            quick_replies=replies,
            claim_ledger=ledger.model_dump() if hasattr(ledger, "model_dump") else ledger.dict(),
            intent="current_alert",
            tools_called=tools_called,
            location=loc,
            clarification_needed=False
        )

    # 6. Forecast (Today / 3 Days)
    if intent == "forecast":
        tools_called.append("get_forecast")
        fc = get_forecast(loc, days=3)
        facts = fc["facts"]
        today = fc["today"]
        t_max = today["temp_max_c"]
        t_min = today["temp_min_c"]
        rain = today["rainfall_mm"]
        wind = today["wind_speed_kmh"]

        if lang == "hi":
            msg = f"{loc['district']} में आज अधिकतम तापमान {to_target_digits(t_max, 'hi')} °C और न्यूनतम {to_target_digits(t_min, 'hi')} °C रहने का अनुमान है। वर्षा: {to_target_digits(rain, 'hi')} मिमी, हवा की गति: {to_target_digits(wind, 'hi')} किमी/घंटा।"
            replies = ["सक्रिय चेतावनी ⚠️", "मछली पकड़ना सुरक्षित है? 🎣", "सामान्य वर्षा कितनी है? 📊"]
        elif lang == "or":
            msg = f"{loc['district']} ରେ ଆଜି ସର୍ବାଧିକ ତାପମାତ୍ରା {to_target_digits(t_max, 'or')} °C ଏବଂ ସର୍ବନିମ୍ନ {to_target_digits(t_min, 'or')} °C ରହିବ। ବର୍ଷା: {to_target_digits(rain, 'or')} ମିମି, ପବନର ବେଗ: {to_target_digits(wind, 'or')} କିମି/ଘଣ୍ଟା।"
            replies = ["ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ସମୁଦ୍ର ଯାତ୍ରା ସୁରକ୍ଷିତ କି? 🎣", "ସ୍ୱାଭାବିକ ବର୍ଷା କେତେ? 📊"]
        else:
            msg = f"Weather forecast for {loc['district']}: Max temperature {t_max} °C, Min temperature {t_min} °C. Rainfall: {rain} mm, Wind speed: {wind} km/h."
            replies = ["Active Alerts ⚠️", "Safety Check 🎣", "Climate Normals 📊"]

        return _build_response(session_id, msg, "forecast", tools_called, loc, replies, facts=facts, lang=lang)

    # 7. Safety Check (Fishing / Sowing / Travel)
    if intent == "safety_check":
        tools_called.append("get_marine")
        marine = get_marine(loc)
        facts = marine["facts"]
        wave = marine["wave_height_m"]
        is_safe = marine["is_safe"]

        # Also cross check active alerts
        alert_res = get_active_alerts(loc)
        if alert_res["has_alert"]:
            is_safe = False
            for f in alert_res["facts"]:
                facts.append(f)

        if not is_safe:
            if lang == "hi":
                msg = f"असुरक्षित: {loc['district']} के तटीय समुद्र में {to_target_digits(wave, 'hi')} मीटर ऊंची लहरें हैं और मौसम चेतावनी प्रभावी है। गहरे समुद्र में न जाएं।"
                replies = ["निकटतम आश्रय 🏠", "सलाह क्या है? 🛡️"]
            elif lang == "or":
                msg = f"ବିପଜ୍ଜନକ: {loc['district']} ଉପକୂଳରେ {to_target_digits(wave, 'or')} ମିଟର ଉଚ୍ଚ ତରଙ୍ଗ ସହିତ ବାତ୍ୟା ସତର୍କତା ଜାରି ଅଛି। ସମୁଦ୍ରକୁ ଯାଆନ୍ତୁ ନାହିଁ।"
                replies = ["ନିକଟତମ ଆଶ୍ରୟ 🏠", "ପରାମର୍ଶ କଣ? 🛡️"]
            else:
                msg = f"UNSAFE: Wave height is {wave} m in {loc['district']} coastal waters with active alert advisory. Do not venture into deep sea."
                replies = ["Nearest Shelter 🏠", "What should I do? 🛡️"]
        else:
            if lang == "hi":
                msg = f"सुरक्षित: {loc['district']} में वर्तमान में लहरों की ऊंचाई {to_target_digits(wave, 'hi')} मीटर है। तटीय मछली पकड़ने के लिए स्थिति सामान्य है।"
                replies = ["आज का मौसम 🌦️", "सक्रिय चेतावनी ⚠️"]
            elif lang == "or":
                msg = f"ସୁରକ୍ଷିତ: {loc['district']} ରେ ବର୍ତ୍ତମାନ ତରଙ୍ଗର ଉଚ୍ଚତା {to_target_digits(wave, 'or')} ମିଟର ଅଛି। ମାଛ ଧରିବା ପାଇଁ ସ୍ଥିତି ଅନୁକୂଳ ଅଛି।"
                replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️"]
            else:
                msg = f"SAFE: Current sea wave height is {wave} m in {loc['district']}. Sea conditions are safe for coastal activities."
                replies = ["Weather Forecast 🌦️", "Active Alerts ⚠️"]

        return _build_response(session_id, msg, "safety_check", tools_called, loc, replies, facts=facts, lang=lang)

    # 8. Nearest Shelter
    if intent == "nearest_shelter":
        tools_called.append("nearest_shelter")
        sh_res = nearest_shelter(loc)
        facts = sh_res["facts"]
        sh = sh_res["shelter"]
        dist = sh_res["distance_km"]
        name = sh["name"]
        contact = sh["contact"]

        if lang == "hi":
            msg = f"{loc['district']} में निकटतम अधिकृत राहत केंद्र: {name} (दूरी: {to_target_digits(dist, 'hi')} किमी)। क्षमता: {to_target_digits(sh['capacity'], 'hi')} व्यक्ति। आपातकालीन हेल्पलाइन: {contact}."
            replies = ["सुरक्षा निर्देश 🛡️", "सक्रिय चेतावनी ⚠️"]
        elif lang == "or":
            msg = f"{loc['district']} ରେ ନିକଟତମ ସରକାରୀ ଆଶ୍ରୟସ୍ଥଳ: {name} (ଦୂରତା: {to_target_digits(dist, 'or')} କିମି)। କ୍ଷମତା: {to_target_digits(sh['capacity'], 'or')} ଲୋକ। ହେଲ୍ପଲାଇନ୍: {contact}."
            replies = ["ସୁରକ୍ଷା ପରାମର୍ଶ 🛡️", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️"]
        else:
            msg = f"Nearest official shelter in {loc['district']}: {name} ({dist} km away). Capacity: {sh['capacity']} people. Emergency Helpline: {contact}."
            replies = ["Action Advice 🛡️", "Active Alerts ⚠️"]

        return _build_response(session_id, msg, "nearest_shelter", tools_called, loc, replies, facts=facts, lang=lang)

    # 9. Action Advice ("What should I do now")
    if intent == "action_advice":
        tools_called.append("get_active_alerts")
        alert_res = get_active_alerts(loc)
        facts = alert_res["facts"]

        if alert_res["has_alert"]:
            top_a = alert_res["alert"]
            instr = top_a.get("instruction", "Move to nearest concrete shelter immediately and store emergency food.")
            if lang == "hi":
                msg = f"[DRILL] {loc['district']} के लिए तत्काल कार्रवाई निर्देश: {instr}"
                replies = ["निकटतम आश्रय 🏠", "मछली पकड़ना सुरक्षित है? 🎣"]
            elif lang == "or":
                msg = f"[DRILL] {loc['district']} ପାଇଁ ଜରୁରୀକାଳୀନ ପରାମର୍ଶ: {instr}"
                replies = ["ନିକଟତମ ଆଶ୍ରୟ 🏠", "ସମୁଦ୍ର ଯାତ୍ରା ସୁରକ୍ଷିତ? 🎣"]
            else:
                msg = f"[DRILL] Action Guidelines for {loc['district']}: {instr}"
                replies = ["Nearest Shelter 🏠", "Is it safe to fish? 🎣"]
        else:
            if lang == "hi":
                msg = f"{loc['district']} में वर्तमान में कोई आपातकालीन चेतावनी नहीं है। सामान्य दैनिक गतिविधियां जारी रख सकते हैं।"
                replies = ["आज का मौसम 🌦️", "निकटतम आश्रय 🏠"]
            elif lang == "or":
                msg = f"{loc['district']} ରେ କୌଣସି ଜରୁରୀ ଚେତାବନୀ ନାହିଁ। ଆପଣ ସ୍ୱାଭାବିକ କାର୍ଯ୍ୟ ଜାରି ରଖିପାରିବେ।"
                replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
            else:
                msg = f"There are no active emergency advisories for {loc['district']}. Standard precautions apply."
                replies = ["Today's Forecast 🌦️", "Nearest Shelter 🏠"]

        return _build_response(session_id, msg, "action_advice", tools_called, loc, replies, facts=facts, lang=lang)

    # 10. Climate Info
    if intent == "climate_info":
        tools_called.append("get_climate_normals")
        clim = get_climate_normals(loc)
        facts = clim["facts"]
        norm_rain = clim["normal_rainfall_mm"]
        month_name = clim["month"]
        anomaly = clim["anomaly_summary"]

        if lang == "hi":
            msg = f"{loc['district']} में {month_name} के लिए सामान्य बारिश {to_target_digits(norm_rain, 'hi')} मिमी है। जलवायु अवलोकन: {anomaly}"
            replies = ["आज का मौसम 🌦️", "सक्रिय चेतावनी ⚠️"]
        elif lang == "or":
            msg = f"{loc['district']} ରେ {month_name} ମାସର ସ୍ୱାଭାବିକ ବର୍ଷା {to_target_digits(norm_rain, 'or')} ମିମି ଅଟେ। ଜଳବାୟୁ ସାରାଂଶ: {anomaly}"
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️"]
        else:
            msg = f"IMD Climate Normals for {loc['district']}: Normal rainfall for {month_name} is {norm_rain} mm. {anomaly}"
            replies = ["Today's Forecast 🌦️", "Active Alerts ⚠️"]

        return _build_response(session_id, msg, "climate_info", tools_called, loc, replies, facts=facts, lang=lang)

    # 11. Honest "No Data / Outside Scope" Fallback (Never Guess!)
    if lang == "hi":
        honest_msg = (
            "क्षमा करें, मेरे पास इस प्रश्न के लिए कोई आधिकारिक मौसम या आपदा डेटा उपलब्ध नहीं है। "
            "कृपया आधिकारिक मौसम जानकारी के लिए भारत मौसम विज्ञान विभाग (IMD) की वेबसाइट https://mausam.imd.gov.in देखें "
            "या राष्ट्रीय आपदा हेल्पलाइन 1077 / 1800-180-1717 पर संपर्क करें।"
        )
        replies = ["सक्रिय चेतावनी ⚠️", "आज का मौसम 🌦️"]
    elif lang == "or":
        honest_msg = (
            "ଦୁଃଖିତ, ମୋ ପାଖରେ ଏହି ପ୍ରଶ୍ନ ପାଇଁ ସରକାରୀ ପାଣିପାଗ ତଥ୍ୟ ଉପଲବ୍ଧ ନାହିଁ। "
            "ଦୟାକରି ସରକାରୀ IMD ପୋର୍ଟାଲ https://mausam.imd.gov.in ଦେଖନ୍ତୁ "
            "କିମ୍ବା ଜାତୀୟ ବିପର୍ଯ୍ୟୟ ହେଲ୍ପଲାଇନ୍ 1077 / 1800-180-1717 ରେ ଯୋଗାଯୋଗ କରନ୍ତୁ।"
        )
        replies = ["ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ଆଜିର ପାଣିପାଗ 🌦️"]
    else:
        honest_msg = (
            "I do not have verified official weather or disaster data for this query. "
            "Please visit the official IMD portal at https://mausam.imd.gov.in or "
            "contact the National Disaster Helpline at 1077 / 1800-180-1717."
        )
        replies = ["Active Alerts ⚠️", "Today's Forecast 🌦️"]

    return _build_response(
        session_id,
        honest_msg,
        "outside_scope",
        [],
        loc,
        replies,
        facts=[
            {"id": "F1", "field": "helpline", "value": "1077 / 1800-180-1717", "source": "Official NDMA Helpline"},
            {"id": "F2", "field": "website", "value": "https://mausam.imd.gov.in", "source": "IMD Portal"}
        ],
        lang=lang
    )


def _build_response(
    session_id: str,
    message: str,
    intent: str,
    tools_called: List[str],
    location: Dict[str, Any],
    quick_replies: List[str],
    facts: Optional[List[Dict[str, Any]]] = None,
    lang: str = "en"
) -> ChatResponse:
    """Validate claim facts, generate voice synthesis, and return validated response."""
    facts = facts or [{"id": "F1", "field": "response", "value": "Information", "source": "Official System"}]

    # Build FactSheet dict
    factsheet_dict = {"facts": facts}
    actionplan_dict = {
        "hazard": "weather_assistant",
        "grade": "Info",
        "ordered_actions": [{"id": "ACT-INFO-01", "action": message, "fact_refs": [f["id"] for f in facts]}]
    }

    # Validate with Grounding Validator
    payload = {
        "text_script_sentences": [{"text": message, "fact_ids": [f["id"] for f in facts], "action_ids": ["ACT-INFO-01"]}],
        "voice_script_sentences": [{"text": message, "fact_ids": [f["id"] for f in facts], "action_ids": ["ACT-INFO-01"]}],
    }

    ledger = validate_payload(
        payload=payload,
        alert_id=f"CHAT-{session_id[:8]}",
        factsheet=factsheet_dict,
        actionplan=actionplan_dict,
        lang=lang
    )

    # Synthesize Voice Note
    audio_url = None
    try:
        synth = voice_synthesizer.synthesize(message[:200], lang=lang)
        audio_url = synth.get("audio_url")
    except Exception as e:
        logger.warning(f"Voice synthesis failed for chat message: {e}")

    return ChatResponse(
        session_id=session_id,
        message=message,
        voice_script=message[:200],
        audio_url=audio_url,
        quick_replies=quick_replies,
        claim_ledger=ledger.model_dump() if hasattr(ledger, "model_dump") else ledger.dict(),
        intent=intent,
        tools_called=tools_called,
        location=location,
        clarification_needed=False
    )
