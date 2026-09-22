"""
Rule-first Intent Router for Citizen Chat.
Provides deterministic keyword/regex matching for the 9 core intents across English, Hindi, and Odia.
"""
import re
from typing import Dict, Any, Tuple, Optional

# Intent rule definitions: regex patterns mapped to intent codes
INTENT_PATTERNS = {
    "registration": [
        r'\b(register|unregister|subscribe|unsubscribe|my\s+phone|sms\s+alerts|stop\s+alerts|opt\s+in|opt\s+out)\b',
        # Hindi
        r'(रजिस्टर|पंजीकरण|अनसब्सक्राइब|अलर्ट\s+बंद|मोबाइल\s+नंबर)',
        # Odia
        r'(ପଞ୍ଜୀକରଣ|ନମ୍ବର\s+ଯୋଡନ୍ତୁ|ଆଲର୍ଟ\s+ବନ୍ଦ)',
    ],
    "change_language": [
        r'\b(change\s+language|switch\s+to\s+(hindi|odia|english)|speak\s+in|in\s+(hindi|odia|english))\b',
        # Hindi
        r'(भाषा\s+बदलें|हिंदी\s+में|अंग्रेजी\s+में|उड़िया\s+में)',
        # Odia
        r'(ଭାଷା\s+ପରିବର୍ତ୍ତନ|ଓଡ଼ିଆରେ\s+କୁହନ୍ତୁ)',
    ],
    "safety_check": [
        r'\b(safe\s+to\s+(go\s+)?(fish|fishing|sea|boat|travel|sow|sowing|farm|venture))\b',
        r'\b(can\s+i\s+(go\s+)?(fish|to\s+sea|travel|venture|sow))\b',
        r'\b(is\s+it\s+safe)\b',
        # Hindi
        r'(मछली\s+पकड़|समुद्र\s+में\s+जाना|सुरक्षित\s+है|नाव\s+चलाना|यात्रा\s+सुरक्षित|बुवाई)',
        # Odia
        r'(ମାଛ\s+ଧରିବା|ସମୁଦ୍ରକୁ\s+ଯିବା|ସୁରକ୍ଷିତ\s+କି|ବୁଣିବା)',
    ],
    "nearest_shelter": [
        r'\b(shelter|nearest\s+shelter|relief\s+camp|evacuation\s+center|where\s+(to\s+)?(evacuate|take\s+shelter|go))\b',
        # Hindi
        r'(निकटतम\s+आश्रय|आश्रय\s+कहाँ|राहत\s+शिविर|कहाँ\s+जाएं|शरण)',
        # Odia
        r'(ନିକଟତମ\s+ଆଶ୍ରୟ|ଆଶ୍ରୟସ୍ଥଳ|ରିଲିଫ\s+କ୍ୟାମ୍ପ|କେଉଁଠିକୁ\s+ଯିବି)',
    ],
    "action_advice": [
        r'\b(what\s+should\s+i\s+do|what\s+to\s+do\s+now|action\s+plan|advice|guidelines|instructions|precautions)\b',
        # Hindi
        r'(क्या\s+करना\s+चाहिए|अब\s+क्या\s+करें|सलाह|निर्देश|उपाय)',
        # Odia
        r'(କଣ\s+କରିବା\s+ଉଚିତ|ଏବେ\s+କଣ\s+କରିବି|ପରାମର୍ଶ|ସତର୍କତା)',
    ],
    "report_incident": [
        r'\b(report|incident|waterlogging|waterlogged|tree\s+fall|fallen\s+tree|road\s+blocked|power\s+outage|wire\s+cut|damage)\b',
        # Hindi
        r'(घटना\s+की\s+रिपोर्ट|जलभराव|पेड़\s+गिर\s+गया|सड़क\s+बंद|बिजली\s+गुल|खंभा\s+गिरा)',
        # Odia
        r'(ଜଳବନ୍ଦୀ|ଗଛ\s+ପଡିଯାଇଛି|ରାସ୍ତା\s+ଅବରୋଧ|ରିପୋର୍ଟ\s+କରନ୍ତୁ)',
    ],
    "climate_info": [
        r'\b(normal\s+rainfall|climate|hotter\s+than\s+usual|historical|past\s+years|anomaly|july\s+rain|usual\s+weather)\b',
        # Hindi
        r'(जलवायु|सामान्य\s+बारिश|जुलाई\s+में\s+बारिश|गर्म\s+था|इतिहास|औसत)',
        # Odia
        r'(ଜଳବାୟୁ|ସ୍ୱାଭାବିକ\s+ବର୍ଷା|ଜୁଲାଇ\s+ମାସରେ|ଅଧିକ\s+ଗରମ|ପୂର୍ବ\s+ବର୍ଷ)',
    ],
    "current_alert": [
        r'\b(alert|warning|cyclone|flood|heatwave|threat|drill|active\s+alert|danger)\b',
        # Hindi
        r'(चेतावनी|अलर्ट|खतरा|चक्रवात|बाढ़|लू)',
        # Odia
        r'(ଚେତାବନୀ|ଆଲର୍ଟ|ବାତ୍ୟା|ବନ୍ୟା|ବିପଦ)',
    ],
    "forecast": [
        r'\b(forecast|weather\s+forecast|rainfall|rain\s+today|rain\s+tomorrow|weather|temperature|3\s+days|how\s+is\s+the\s+weather)\b',
        # Hindi
        r'(मौसम|पूर्वानुमान|आज\s+का\s+मौसम|कल\s+का\s+मौसम|बारिश\s+होगी|तापमान)',
        # Odia
        r'(ପାଣିପାଗ|ପୂର୍ବାନୁମାନ|ଆଜିର\s+ପାଣିପାଗ|ବର୍ଷା\s+ହେବ|ତାପମାତ୍ରା)',
    ],
}


def classify_intent(message: str) -> str:
    """
    Rule-first intent classifier.
    Returns matching intent string or 'outside_scope'.
    """
    text = message.strip().lower()

    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return intent

    # Check for general greeting
    if re.search(r'\b(hi|hello|namaste|namaskar|hey)\b', text, re.IGNORECASE):
        return "greeting"

    return "outside_scope"
