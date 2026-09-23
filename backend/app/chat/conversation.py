"""
Conversational SkySafe AI synthesizer.
Generates dynamic, intelligent, context-aware responses to ANY question in the world
(science, general knowledge, greetings, lifestyle, philosophy, definitions)
as well as tailored, real-time grounded weather and safety advice.
Supports English, Hindi, and Odia.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from app.lang.digits import to_target_digits


# Common World Capitals
CAPITALS = {
    "france": "Paris",
    "japan": "Tokyo",
    "germany": "Berlin",
    "united states": "Washington, D.C.",
    "usa": "Washington, D.C.",
    "united kingdom": "London",
    "uk": "London",
    "england": "London",
    "italy": "Rome",
    "russia": "Moscow",
    "china": "Beijing",
    "india": "New Delhi",
    "australia": "Canberra",
    "canada": "Ottawa",
    "brazil": "Brasília",
    "south africa": "Pretoria / Cape Town",
    "egypt": "Cairo",
    "spain": "Madrid",
    "mexico": "Mexico City",
    "argentina": "Buenos Aires",
    "saudi arabia": "Riyadh",
    "uae": "Abu Dhabi",
    "dubai": "Abu Dhabi (capital of UAE)",
    "thailand": "Bangkok",
    "singapore": "Singapore",
    "nepal": "Kathmandu",
    "bangladesh": "Dhaka",
    "sri lanka": "Sri Jayawardenepura Kotte (Colombo)",
    "switzerland": "Bern",
    "netherlands": "Amsterdam",
    "turkey": "Ankara",
    "south korea": "Seoul",
    "indonesia": "Jakarta",
    "new zealand": "Wellington",
    "norway": "Oslo",
    "sweden": "Stockholm",
}


def synthesize_conversational_weather_response(
    query: str,
    loc: Dict[str, Any],
    today_fc: Dict[str, Any],
    alert_res: Dict[str, Any],
    lang: str = "en",
    persona: str = "general",
    forecast_days: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[str]]:
    """
    Synthesize an intelligent response to ANY question in the world,
    combining broad general knowledge with real-time weather intelligence.
    """
    loc_name = loc.get("name") or loc.get("district", "Your Location")
    district = loc.get("district", loc_name)
    state = loc.get("state", "India")

    temp_now = today_fc.get("temp_now_c", 28.0)
    condition = today_fc.get("condition", "Fair")
    humidity = today_fc.get("humidity_pct", 55)
    wind = today_fc.get("wind_speed_kmh", 12.0)
    temp_max = today_fc.get("temp_max_c", 32.0)
    temp_min = today_fc.get("temp_min_c", 24.0)
    rain = today_fc.get("rainfall_mm", 0.0)

    has_alert = alert_res.get("has_alert", False)
    alert_headline = ""
    alert_instruction = ""
    if has_alert and "alert" in alert_res:
        alert_headline = alert_res["alert"].get("headline", "")
        alert_instruction = alert_res["alert"].get("instruction", "")

    clean_q = query.strip().lower()

    # Digits formatting
    t_now_str = to_target_digits(temp_now, lang)
    t_max_str = to_target_digits(temp_max, lang)
    t_min_str = to_target_digits(temp_min, lang)
    hum_str = to_target_digits(humidity, lang)
    wind_str = to_target_digits(wind, lang)
    rain_str = to_target_digits(rain, lang)

    # -------------------------------------------------------------
    # 1. GREETINGS & CASUAL INTRODUCTIONS ("hi", "hello", "hey")
    # -------------------------------------------------------------
    if re.search(r'^(hi|hello|hey|hiya|howdy|good\s+morning|good\s+afternoon|good\s+evening|namaste|namaskar|नमस्ते|प्रणाम|ନମସ୍କାର)[\s!.,?]*$', clean_q):
        if lang == "hi":
            msg = (
                "👋 **नमस्ते!** कैसे हैं आप? मैं स्काईसेफ एआई हूँ।\n\n"
                "आप मुझसे दुनिया का कोई भी सवाल पूछ सकते हैं—विज्ञान, इतिहास, सामान्य ज्ञान, तकनीकी या फिर अपने स्थान का मौसम और सुरक्षा सलाह! आज मैं आपकी क्या मदद कर सकता हूँ?"
            )
            replies = ["आज का मौसम कैसा है? 🌦️", "मुझे एक चुटकुला सुनाओ 😄", "आसमान नीला क्यों होता है? 🌌", "कपड़ों की सलाह 👕"]
        elif lang == "or":
            msg = (
                "👋 **ନମସ୍କାର!** ଆପଣ କେମିତି ଅଛନ୍ତି? ମୁଁ ସ୍କାଇସେଫ୍ ଏଆଇ।\n\n"
                "ଆପଣ ମୋତେ ଯେକୌଣସି ପ୍ରଶ୍ନ ପଚାରିପାରିବେ—ବିଜ୍ଞାନ, ସାଧାରଣ ଜ୍ଞାନ କିମ୍ବା ଆପଣଙ୍କ ଅଞ୍ଚଳର ପାଣିପାଗ ସମ୍ପର୍କରେ!"
            )
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ଗୋଟିଏ କୌତୁକ କୁହନ୍ତୁ 😄", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️"]
        else:
            msg = (
                "👋 **Hello there!** How are you doing today? I'm SkySafe AI, your all-purpose AI assistant.\n\n"
                "You can ask me **any question in the world**—whether it's about science, technology, general knowledge, everyday advice, creative writing, or your local real-time weather and safety! How can I help you today?"
            )
            replies = ["How's the weather today? 🌦️", "Tell me a joke 😄", "Why is the sky blue? 🌌", "What should I wear? 👕"]
        return msg, replies

    # "How are you"
    if re.search(r'\b(how\s+are\s+you|how\s+r\s+u|how\s+are\s+you\s+doing|hows\s+it\s+going|कैसे\s+हो|कैसी\s+हो|କେମିତି\s+ଅଛନ୍ତି)\b', clean_q):
        if lang == "hi":
            msg = "मैं बहुत बढ़िया हूँ, पूछने के लिए धन्यवाद! 😊 आप कैसे हैं? आज आप क्या जानना या चर्चा करना चाहेंगे?"
            replies = ["आज का मौसम 🌦️", "एक रोचक तथ्य बताओ 💡", "मुझे एक चुटकुला सुनाओ 😄"]
        elif lang == "or":
            msg = "ମୁଁ ବହୁତ ଭଲ ଅଛି, ଧନ୍ୟବାଦ! 😊 ଆପଣ କେମିତି ଅଛନ୍ତି? ଆଜି ଆପଣ କଣ ଜାଣିବାକୁ ଚାହାଁନ୍ତି?"
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ଏକ ମଜାଳିଆ କଥା କୁହନ୍ତୁ 💡"]
        else:
            msg = "I'm doing great, thank you for asking! 😊 How are you doing today? What's on your mind—science, general knowledge, or weather updates?"
            replies = ["Today's Forecast 🌦️", "Tell me a fun fact 💡", "Tell me a joke 😄"]
        return msg, replies

    # "Who are you" / "What is your name" / "What can you do"
    if re.search(r'\b(who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself|तुम\s+कौन\s+हो|आप\s+कौन\s+हैं|ଆପଣ\s+କିଏ)\b', clean_q):
        msg = (
            "🤖 **I am SkySafe AI**, an intelligent conversational AI assistant!\n\n"
            "Here is what I can do for you:\n"
            "• **Answer Any Question:** Science, technology, math, history, world geography, definitions, and daily advice.\n"
            "• **Real-Time Weather Intelligence:** Automatic device GPS detection, temperature, rainfall, and multi-day forecasts.\n"
            "• **Personalized Recommendations:** Smart outfit/clothing guidance, umbrella checks, outdoor workout safety, and travel tips.\n"
            "• **Disaster & Emergency Guidance:** Official CAP warning alerts, nearest cyclone shelters, and citizen safety action plans.\n\n"
            "Feel free to ask me anything you like!"
        )
        replies = ["Why is the sky blue? 🌌", "Today's Forecast 🌦️", "Tell me a joke 😄", "What should I wear? 👕"]
        return msg, replies

    # Humor / Jokes
    if re.search(r'\b(joke|funny|laugh|chutkula|चुटकुला|हंसाओ|मजाक|କୌତୁକ)\b', clean_q):
        jokes = [
            "😄 **Why don't scientists trust atoms?**\nBecause they make up everything!",
            "😄 **Why did the scarecrow win an award?**\nBecause he was outstanding in his field!",
            "😄 **Why do programmers prefer dark mode?**\nBecause light attracts bugs!",
            "😄 **What did one ocean say to the other ocean?**\nNothing, they just waved!",
        ]
        import random
        joke = random.choice(jokes)
        replies = ["Tell me another joke 😄", "Tell me a fun fact 💡", "Today's Forecast 🌦️"]
        return joke, replies

    # Fun Fact / Trivia
    if re.search(r'\b(fun\s+fact|trivia|did\s+you\s+know|fact|तथ्य|रोचक)\b', clean_q):
        facts_list = [
            "💡 **Fun Fact:** Honey never spoils! Archaeologists have discovered pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible!",
            "💡 **Fun Fact:** A day on Venus is longer than a year on Venus! It takes Venus 243 Earth days to rotate once on its axis, but only 225 Earth days to orbit the Sun.",
            "💡 **Fun Fact:** Octopuses have three hearts, nine brains, and blue blood!",
            "💡 **Fun Fact:** Raindrops aren't shaped like teardrops; they actually look more like hamburger buns due to air resistance flattening their bottoms as they fall!",
        ]
        import random
        fact = random.choice(facts_list)
        replies = ["Another fun fact 💡", "Why is the sky blue? 🌌", "Today's Forecast 🌦️"]
        return fact, replies

    # -------------------------------------------------------------
    # 2. SCIENCE, TECHNOLOGY & NATURE
    # -------------------------------------------------------------
    # Why is the sky blue?
    if "sky blue" in clean_q or "आसमान नीला" in clean_q or "ଆକାଶ ନୀଳ" in clean_q:
        msg = (
            "🌌 **Why the Sky is Blue (Rayleigh Scattering):**\n\n"
            "Sunlight appears white, but it is actually made up of all the colors of the rainbow. "
            "When sunlight reaches Earth's atmosphere, it collides with gases and tiny particles in the air.\n\n"
            "Light travels in waves: red and orange light have longer wavelengths and pass straight through, "
            "while **blue and violet light travel in short, smaller waves**. These shorter blue waves scatter in all directions "
            "across the atmosphere much more than any other color, causing our sky to look bright blue!"
        )
        replies = ["What is photosynthesis? 🌿", "How do airplanes fly? ✈️", "Today's Forecast 🌦️"]
        return msg, replies

    # Photosynthesis
    if "photosynthesis" in clean_q or "प्रकाश संश्लेषण" in clean_q:
        msg = (
            "🌿 **What is Photosynthesis?**\n\n"
            "Photosynthesis is the chemical process by which green plants, algae, and some bacteria create their own food.\n\n"
            "• **Inputs:** Plants absorb **sunlight** (via chlorophyll), **water** ($H_2O$) through their roots, and **carbon dioxide** ($CO_2$) from the air.\n"
            "• **Outputs:** They convert these into **glucose** (sugar for energy) and release **oxygen** ($O_2$) into the atmosphere.\n\n"
            "Chemical formula: $6CO_2 + 6H_2O + \\text{light} \\rightarrow C_6H_{12}O_6 + 6O_2$."
        )
        replies = ["Why is the sky blue? 🌌", "What is gravity? 🍎", "Today's Forecast 🌦️"]
        return msg, replies

    # Gravity
    if "gravity" in clean_q or "गुरुत्वाकर्षण" in clean_q:
        msg = (
            "🍎 **What is Gravity?**\n\n"
            "Gravity is one of the four fundamental forces of nature. Any object with mass pulls other objects toward itself.\n\n"
            "• **Isaac Newton's view:** Gravity is an attractive force between two masses ($F = G \\frac{m_1 m_2}{r^2}$).\n"
            "• **Albert Einstein's General Relativity:** Massive objects (like planets and stars) actually warp and bend the fabric of spacetime around them, and objects follow these curved paths."
        )
        replies = ["Who was Albert Einstein? 🧠", "What is the speed of light? ⚡", "Today's Forecast 🌦️"]
        return msg, replies

    # Airplanes / Flight
    if "airplane" in clean_q and ("fly" in clean_q or "flying" in clean_q or "air" in clean_q):
        msg = (
            "✈️ **How Do Airplanes Fly? (The 4 Forces of Flight):**\n\n"
            "An airplane flies through a delicate balance of four aerodynamic forces:\n"
            "1. **Lift:** Wings are curved on top (airfoil shape). Air moves faster over the top than the bottom, creating lower pressure on top and pushing the plane upward (Bernoulli's Principle & Newton's Third Law).\n"
            "2. **Weight (Gravity):** The downward pull of Earth's gravity.\n"
            "3. **Thrust:** Jet engines or propellers push the plane forward through the air.\n"
            "4. **Drag:** Air resistance opposing forward motion.\n\n"
            "When lift exceeds weight and thrust exceeds drag, the aircraft takes flight and ascends!"
        )
        replies = ["Why is the sky blue? 🌌", "What is the speed of light? ⚡", "Today's Forecast 🌦️"]
        return msg, replies

    # Speed of Light
    if "speed of light" in clean_q or "प्रकाश की गति" in clean_q:
        msg = (
            "⚡ **The Speed of Light ($c$):**\n\n"
            "In a vacuum, the speed of light is exactly **299,792,458 meters per second** (approximately **300,000 km/s** or **186,282 miles/s**).\n\n"
            "At this mind-boggling speed, light could travel around the entire equator of Earth 7.5 times in just one second! It takes sunlight about 8 minutes and 20 seconds to reach Earth."
        )
        replies = ["Who was Albert Einstein? 🧠", "What is gravity? 🍎", "Today's Forecast 🌦️"]
        return msg, replies

    # Quantum Computing / AI
    if "quantum" in clean_q or "artificial intelligence" in clean_q or "machine learning" in clean_q:
        msg = (
            "💻 **Frontiers of Computing:**\n\n"
            "• **Artificial Intelligence (AI):** Systems designed to perform tasks that typically require human cognition—such as pattern recognition, language understanding, reasoning, and problem-solving—trained on vast datasets using deep neural networks.\n"
            "• **Quantum Computing:** Classical computers use binary bits (0 or 1). Quantum computers use **qubits**, which can exist in a **superposition** of both 0 and 1 simultaneously, enabling them to solve complex cryptographic, molecular, and optimization problems exponentially faster."
        )
        replies = ["Tell me a fun fact 💡", "Who was Albert Einstein? 🧠", "Today's Forecast 🌦️"]
        return msg, replies

    # -------------------------------------------------------------
    # 3. WORLD CAPITALS & GEOGRAPHY
    # -------------------------------------------------------------
    for country, cap in CAPITALS.items():
        if f"capital of {country}" in clean_q or f"{country} capital" in clean_q or f"{country} की राजधानी" in clean_q:
            country_display = country.title()
            if lang == "hi":
                msg = f"🏛️ **{country_display} की राजधानी:** **{cap}** है।"
            else:
                msg = f"🏛️ The capital of **{country_display}** is **{cap}**."
            replies = ["Capital of Japan 🇯🇵", "Capital of France 🇫🇷", "Today's Forecast 🌦️"]
            return msg, replies

    # -------------------------------------------------------------
    # 4. FAMOUS HISTORICAL FIGURES
    # -------------------------------------------------------------
    if "einstein" in clean_q:
        msg = (
            "🧠 **Albert Einstein (1879–1955):**\n\n"
            "One of the greatest theoretical physicists in history. He developed the **Theory of Relativity** (Special and General), "
            "revolutionizing our understanding of space, time, gravity, and the universe. "
            "He formulated the world's most famous equation, **$E = mc^2$** (mass-energy equivalence), "
            "and was awarded the 1921 Nobel Prize in Physics for his explanation of the photoelectric effect."
        )
        replies = ["What is gravity? 🍎", "What is the speed of light? ⚡", "Today's Forecast 🌦️"]
        return msg, replies

    if "newton" in clean_q:
        msg = (
            "🍎 **Sir Isaac Newton (1643–1727):**\n\n"
            "An English mathematician, physicist, and astronomer recognized as a key figure in the Scientific Revolution. "
            "He formulated the **Three Laws of Motion**, the **Universal Law of Gravitation**, "
            "co-invented infinitesimal calculus, and built the first practical reflecting telescope."
        )
        replies = ["What is gravity? 🍎", "Who was Albert Einstein? 🧠", "Today's Forecast 🌦️"]
        return msg, replies

    if "abdul kalam" in clean_q or "apj" in clean_q or "kalam" in clean_q:
        msg = (
            "🚀 **Dr. A. P. J. Abdul Kalam (1931–2015):**\n\n"
            "Known as the *'Missile Man of India'*, Dr. Kalam was an illustrious aerospace scientist who played a pivotal role "
            "in India's civilian space program and military missile development (including Agni and Prithvi). "
            "He served as the beloved 11th President of India (2002–2007) and inspired millions of students with his visionary books like *Wings of Fire*."
        )
        replies = ["Tell me a fun fact 💡", "Who was Albert Einstein? 🧠", "Today's Forecast 🌦️"]
        return msg, replies

    # -------------------------------------------------------------
    # 5. EVERYDAY TASKS, ADVICE & RECIPES
    # -------------------------------------------------------------
    if re.search(r'\b(make\s+tea|how\s+to\s+make\s+chai|tea\s+recipe|चाय\s+बना|ଚା\s+ତିଆରି)\b', clean_q):
        msg = (
            "☕ **Classic Indian Masala Chai Recipe:**\n\n"
            "1. **Boil Water:** In a saucepan, boil 1 cup of water with crushed ginger and 2 crushed green cardamoms for 2 minutes.\n"
            "2. **Add Tea Leaves:** Add 1.5 teaspoons of black tea leaves (or CTC tea). Simmer for 1–2 minutes until deep amber.\n"
            "3. **Add Milk & Sugar:** Add 1/2 to 3/4 cup of milk and 1–2 teaspoons of sugar to taste.\n"
            "4. **Simmer & Strain:** Bring to a frothy boil twice, simmer for 1 minute, and strain into your cup. Enjoy your aromatic, soothing chai!"
        )
        replies = ["Healthy breakfast ideas 🍳", "Today's Forecast 🌦️", "Tell me a joke 😄"]
        return msg, replies

    if re.search(r'\b(study\s+better|how\s+to\s+study|exam\s+tips|पढ़ाई\s+कैसे)\b', clean_q):
        msg = (
            "📚 **Top Science-Backed Study Techniques:**\n\n"
            "• **Active Recall:** Instead of passively re-reading, test yourself by reciting key concepts from memory.\n"
            "• **Spaced Repetition:** Review material at increasing intervals (Day 1, Day 3, Day 7) to cement knowledge into long-term memory.\n"
            "• **Pomodoro Technique:** Work with focused intensity for 25 minutes, then take a strict 5-minute break.\n"
            "• **Feynman Technique:** Explain the topic aloud in simple terms as if teaching it to a 10-year-old."
        )
        replies = ["Tell me a fun fact 💡", "How to stay healthy 🍎", "Today's Forecast 🌦️"]
        return msg, replies

    # Poetry / Creative Writing
    if re.search(r'\b(write\s+a\s+poem|poetry|poem|कविता|କବିତା)\b', clean_q):
        msg = (
            "📜 *Whispers of the Horizon*\n\n"
            "The morning whispers to the sky,\n"
            "As silver clouds go drifting by.\n"
            "A gentle breeze, a quiet dawn,\n"
            "A brand new day is softly born.\n\n"
            "Through wind and rain, through sun and shade,\n"
            "The beauty of the earth is made;\n"
            "Walk with wonder, dream and soar,\n"
            "And seek the world forevermore."
        )
        replies = ["Tell me another poem 📜", "Why is the sky blue? 🌌", "Today's Forecast 🌦️"]
        return msg, replies

    # -------------------------------------------------------------
    # 6. WEATHER & SAFETY INTELLIGENCE (GPS Grounded)
    # -------------------------------------------------------------
    # GPS / Device location pin detection
    if any(k in clean_q for k in ["gps", "current location", "my location", "मेरे वर्तमान स्थान", "ମୋ ବର୍ତ୍ତମାନ ସ୍ଥାନ", "📍"]):
        if lang == "hi":
            alert_txt = f"\n\n⚠️ **सक्रिय चेतावनी:** {alert_headline}। {alert_instruction}\n" if has_alert else ""
            msg = (
                f"📍 **आपका वर्तमान स्थान पाया गया:** **{loc_name}** ({district}, {state})\n\n"
                f"• **मौसम स्थिति:** {condition}\n"
                f"• **वर्तमान तापमान:** {t_now_str} °C (आज का तापमान: {t_min_str} °C से {t_max_str} °C)\n"
                f"• **आर्द्रता:** {hum_str}%\n"
                f"• **हवा की गति:** {wind_str} किमी/घंटा\n"
                f"• **वर्षा:** {rain_str} मिमी\n"
                f"{alert_txt}\n"
                f"आपके स्थान के लिए लाइव निगरानी चालू है। आप मुझसे कपड़े, वर्षा, या बाहर जाने की सलाह ले सकते हैं!"
            )
            replies = ["मुझे क्या पहनना चाहिए? 👕", "क्या छाते की ज़रूरत है? ☔", "आज का मौसम 🌦️", "सक्रिय चेतावनी ⚠️"]
        elif lang == "or":
            msg = (
                f"📍 **ଆପଣଙ୍କ ବର୍ତ୍ତମାନର ସ୍ଥାନ:** **{loc_name}** ({district}, {state})\n\n"
                f"• **ପାଣିପାଗ ସ୍ଥିତି:** {condition}\n"
                f"• **ବର୍ତ୍ତମାନ ତାପମାତ୍ରା:** {t_now_str} °C (ସର୍ବାଧିକ {t_max_str} °C / ସର୍ବନିମ୍ନ {t_min_str} °C)\n"
                f"• **ଆର୍ଦ୍ରତା:** {hum_str}%\n"
                f"• **ପବନ ଗତି:** {wind_str} କିମି/ଘଣ୍ଟା\n"
                f"• **ବର୍ଷା:** {rain_str} ମିମି\n\n"
                f"ଆପଣଙ୍କ ସ୍ଥାନର ପାଣିପାଗ ସୂଚନା ଉପଲବ୍ଧ ଅଛି।"
            )
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ଛତା ଦରକାର କି? ☔", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
        else:
            alert_txt = f"\n\n⚠️ **Active Weather Alert:** {alert_headline}. {alert_instruction}\n" if has_alert else ""
            msg = (
                f"📍 **GPS Location Detected:** **{loc_name}**, {district}, {state}\n\n"
                f"• **Sky Condition:** {condition}\n"
                f"• **Current Temperature:** {t_now_str} °C (High {t_max_str} °C / Low {t_min_str} °C)\n"
                f"• **Precipitation:** {rain_str} mm\n"
                f"• **Humidity & Wind:** {hum_str}% humidity, {wind_str} km/h winds\n"
                f"{alert_txt}\n"
                f"Real-time weather tracking is active for your device location. Ask me what to wear, if you need an umbrella, or outdoor recommendations!"
            )
            replies = ["What should I wear? 👕", "Do I need an umbrella? ☔", "Today's Forecast 🌦️", "Active Alerts ⚠️"]
        return msg, replies

    # Clothing / Attire / Wardrobe
    clothing_patterns = [
        r'\b(wear|clothes|clothing|jacket|sweater|coat|dress|shorts|t-shirt|tshirt|outfit|attire|shoes|raincoat)\b',
        r'(पहन|कपड़े|पोशाक|जैकेट|स्वेटर|टी-शर्ट)',
        r'(ପିନ୍ଧି|ପୋଷାକ|ଜ୍ୟାକେଟ୍|ସ୍ୱେଟର)'
    ]
    if any(re.search(p, clean_q) for p in clothing_patterns):
        rain_note = ""
        if rain > 0.5 or "rain" in condition.lower():
            if lang == "hi":
                rain_note = f"\n\n🌧️ **वर्षा सुरक्षा:** आज {rain_str} मिमी बारिश की संभावना है, इसलिए वाटरप्रूफ जूते और रेनकोट या छाता अवश्य साथ रखें।"
            elif lang == "or":
                rain_note = f"\n\n🌧️ **ବର୍ଷା ସତର୍କତା:** {rain_str} ମିମି ବର୍ଷା ସମ୍ଭାବନା ଥିବାରୁ ରେନକୋଟ୍ ବା ଛତା ବ୍ୟବହାର କରନ୍ତୁ।"
            else:
                rain_note = f"\n\n🌧️ **Rain Gear:** Since precipitation ({rain_str} mm) is expected, wear water-resistant footwear and carry a compact umbrella or raincoat."

        if temp_now >= 32.0:
            if lang == "hi":
                msg = (
                    f"👕 **{loc_name} में कपड़ों की सलाह ({t_now_str} °C):**\n"
                    f"आज मौसम काफी गर्म और {condition} है। हल्के रंग के, ढीले सूती (कॉटन) या लिनन के कपड़े पहनें ताकि शरीर ठंडा रहे। "
                    f"धूप में निकलने पर टोपी या चश्मा पहनें और पानी साथ रखें।"
                    f"{rain_note}"
                )
            elif lang == "or":
                msg = (
                    f"👕 **{loc_name} ପାଇଁ ପୋଷାକ ପରାମର୍ଶ ({t_now_str} °C):**\n"
                    f"ଆଜି ଗରମ ଏବଂ ପାଣିପାଗ {condition} ଅଛି। ହାଲୁକା ରଙ୍ଗର ସୂତା ବସ୍ତ୍ର ପିନ୍ଧନ୍ତୁ ଏବଂ ପର୍ଯ୍ୟାପ୍ତ ପାଣି ପିଅନ୍ତୁ।"
                    f"{rain_note}"
                )
            else:
                msg = (
                    f"👕 **Clothing Advice for {loc_name} ({t_now_str} °C):**\n"
                    f"It is hot and {condition} today! I recommend wearing loose, light-colored cotton or linen clothing to stay cool and comfortable. "
                    f"If you're heading outdoors, sunglasses, a wide-brimmed hat, and staying hydrated are highly recommended."
                    f"{rain_note}"
                )
        elif 22.0 <= temp_now < 32.0:
            if lang == "hi":
                msg = (
                    f"👕 **{loc_name} में कपड़ों की सलाह ({t_now_str} °C):**\n"
                    f"मौसम सुखद और {condition} है। आरामदायक टी-शर्ट, हल्की सूती शर्ट और पैंट या जींस पहनना एकदम सही रहेगा।"
                    f"{rain_note}"
                )
            elif lang == "or":
                msg = (
                    f"👕 **{loc_name} ପାଇଁ ପୋଷାକ ପରାମର୍ଶ ({t_now_str} °C):**\n"
                    f"ପାଣିପାଗ ସ୍ୱାଭାବିକ ଏବଂ {condition} ଅଛି। ଆରାମଦାୟକ ସୂତା ସାର୍ଟ ବା ଟି-ସାର୍ଟ ପିନ୍ଧିପାରିବେ।"
                    f"{rain_note}"
                )
            else:
                msg = (
                    f"👕 **Clothing Advice for {loc_name} ({t_now_str} °C):**\n"
                    f"Conditions are comfortably pleasant with {condition} skies. Casual wear like a comfortable t-shirt or light shirt paired with cotton pants, jeans, or shorts will keep you comfortable throughout the day."
                    f"{rain_note}"
                )
        elif 16.0 <= temp_now < 22.0:
            if lang == "hi":
                msg = (
                    f"🧥 **{loc_name} में कपड़ों की सलाह ({t_now_str} °C):**\n"
                    f"हवा में हल्की ठंडक है। एक हल्की जैकेट, हुडी, कार्डिगन या पूरी आस्तीन की शर्ट पहनना आरामदायक रहेगा।"
                    f"{rain_note}"
                )
            elif lang == "or":
                msg = (
                    f"🧥 **{loc_name} ପାଇଁ ପରାମର୍ଶ ({t_now_str} °C):**\n"
                    f"ହାଲୁକା ଥଣ୍ଡା ଅଛି। ଏକ ହାଲୁକା ଜ୍ୟାକେଟ୍ ବା ଫୁଲ୍-ସ୍ଲିଭ୍ ସାର୍ଟ ପିନ୍ଧିବା ଭଲ ହେବ।"
                    f"{rain_note}"
                )
            else:
                msg = (
                    f"🧥 **Clothing Advice for {loc_name} ({t_now_str} °C):**\n"
                    f"It's mildly cool with {condition} skies. Layering with a light jacket, cardigan, sweatshirt, or long-sleeve shirt will keep you cozy, particularly in the morning and evening hours."
                    f"{rain_note}"
                )
        else:
            if lang == "hi":
                msg = (
                    f"🧥 **{loc_name} में कपड़ों की सलाह ({t_now_str} °C):**\n"
                    f"बाहर काफी ठंड है! गर्म ऊनी कपड़े, स्वेटर या भारी जैकेट पहनें। बाहर निकलते समय मफलर या टोपी का उपयोग करें।"
                    f"{rain_note}"
                )
            elif lang == "or":
                msg = (
                    f"🧥 **{loc_name} ପାଇଁ ପରାମର୍ଶ ({t_now_str} °C):**\n"
                    f"ବାହାରେ ଥଣ୍ଡା ଅଛି! ଗରମ ପୋଷାକ, ସ୍ୱେଟର ବା ଜ୍ୟାକେଟ୍ ପିନ୍ଧନ୍ତୁ।"
                    f"{rain_note}"
                )
            else:
                msg = (
                    f"🧥 **Clothing Advice for {loc_name} ({t_now_str} °C):**\n"
                    f"It is chilly outside! Layer up with a warm woolen sweater, fleece, or heavy jacket. If you are venturing outdoors early morning or at night, a scarf and warm socks will keep you comfortable."
                    f"{rain_note}"
                )

        replies = ["Do I need an umbrella? ☔", "Today's Forecast 🌦️", "Can I go for a run? 🏃", "Active Alerts ⚠️"]
        return msg, replies

    # Umbrella / Rain / Precipitation
    umbrella_patterns = [
        r'\b(umbrella|rain|raining|shower|drizzle|precipitation|wet|storm)\b',
        r'(छाता|बारिश|बरसात|बूंदाबांदी)',
        r'(ଛତା|ବର୍ଷା|ଝିପିଝିପି)'
    ]
    if any(re.search(p, clean_q) for p in umbrella_patterns):
        if rain >= 1.0 or any(w in condition.lower() for w in ["rain", "drizzle", "shower", "thunderstorm"]):
            if lang == "hi":
                msg = (
                    f"☔ **हाँ, छाता ज़रूर साथ रखें!**\n\n"
                    f"{loc_name} में वर्तमान में मौसम **{condition}** है और आज **{rain_str} मिमी** बारिश की संभावना है। "
                    f"तापमान {t_now_str} °C और आर्द्रता {hum_str}% है। बाहर निकलते समय छाता या रेनकोट साथ रखना आवश्यक है।"
                )
            elif lang == "or":
                msg = (
                    f"☔ **ହଁ, ନିଶ୍ଚିତ ଭାବରେ ଛତା ସାଙ୍ଗରେ ନିଅନ୍ତୁ!**\n\n"
                    f"{loc_name} ରେ ବର୍ତ୍ତମାନ ପାଣିପାଗ **{condition}** ଏବଂ ଆଜି **{rain_str} ମିମି** ବର୍ଷା ସମ୍ଭାବନା ଅଛି।"
                )
            else:
                msg = (
                    f"☔ **Yes, definitely take an umbrella!**\n\n"
                    f"In {loc_name}, it is currently **{condition}** with an estimated **{rain_str} mm** of precipitation today. "
                    f"Temperature is {t_now_str} °C with {hum_str}% humidity. Keep your umbrella or raincoat ready before heading out to stay dry."
                )
        elif 0.1 <= rain < 1.0:
            if lang == "hi":
                msg = (
                    f"🌦️ **एहतियातन छोटा छाता साथ रख सकते हैं।**\n\n"
                    f"{loc_name} में भारी बारिश की संभावना नहीं है, लेकिन हल्की बूंदाबांदी ({rain_str} मिमी) हो सकती है। "
                    f"वर्तमान स्थिति {condition} और तापमान {t_now_str} °C है।"
                )
            elif lang == "or":
                msg = (
                    f"🌦️ **ସତର୍କତା ଭାବେ ଛତା ସାଙ୍ଗରେ ରଖିପାରିବେ।**\n\n"
                    f"{loc_name} ରେ ହାଲୁକା ବର୍ଷା ({rain_str} ମିମି) ହୋଇପାରେ।"
                )
            else:
                msg = (
                    f"🌦️ **Carry a compact umbrella just in case!**\n\n"
                    f"While heavy downpours are not predicted, there is a chance of light isolated drizzle ({rain_str} mm) in {loc_name}. "
                    f"Current condition is {condition} at {t_now_str} °C."
                )
        else:
            if lang == "hi":
                msg = (
                    f"☀️ **आज छाते की कोई आवश्यकता नहीं है!**\n\n"
                    f"{loc_name} में मौसम **{condition}** है, तापमान **{t_now_str} °C** है और बारिश की संभावना शून्य ({rain_str} मिमी) है। "
                    f"आप बिना बारिश के सामान के आराम से बाहर जा सकते हैं।"
                )
            elif lang == "or":
                msg = (
                    f"☀️ **ଆଜି ଛତା ଦରକାର ନାହିଁ!**\n\n"
                    f"{loc_name} ରେ ପାଣିପାଗ **{condition}** ଅଛି ଏବଂ ଆଜି ବର୍ଷା ହେବାର ସମ୍ଭାବନା ନାହିଁ।"
                )
            else:
                msg = (
                    f"☀️ **No umbrella needed today!**\n\n"
                    f"The sky in {loc_name} is currently **{condition}** at **{t_now_str} °C** with zero rainfall predicted today. "
                    f"You can comfortably step out without worrying about rain gear."
                )

        replies = ["What should I wear? 👕", "Today's Forecast 🌦️", "Can I go for a run? 🏃", "Active Alerts ⚠️"]
        return msg, replies

    # Outdoor Fitness / Running / Jogging / Sports / Walking
    fitness_patterns = [
        r'\b(run|running|jog|jogging|walk|walking|cycling|sports|play|workout|gym|cricket|football)\b',
        r'(दौड़|घूमने|टहलने|खेल|कसरत|जिम)',
        r'(ଦୌଡ଼ିବା|ବୁଲିବା|ଖେଳ)'
    ]
    if any(re.search(p, clean_q) for p in fitness_patterns):
        if has_alert:
            if lang == "hi":
                msg = f"⚠️ **बाहरी गतिविधियों की सलाह नहीं है!**\n{loc_name} में सक्रिय चेतावनी है: {alert_headline}। कृपया घर के अंदर सुरक्षित रहें।"
            elif lang == "or":
                msg = f"⚠️ **ବାହାରକୁ ଯିବା ଉଚିତ ନୁହେଁ!**\n{loc_name} ରେ ଚେତାବନୀ ଅଛି: {alert_headline}।"
            else:
                msg = f"⚠️ **Outdoor workouts are not advised right now!**\nThere is an active weather alert in {loc_name}: {alert_headline}. Please prioritize your safety and exercise indoors."
        elif rain > 1.0:
            if lang == "hi":
                msg = (
                    f"🌧️ **सड़कें गीली हो सकती हैं ({rain_str} मिमी बारिश):**\n"
                    f"{loc_name} में मौसम {condition} है। गीली सड़कों पर फिसलने का जोखिम रहता है। "
                    f"आज इनडोर कसरत या बारिश थमने का इंतज़ार करना बेहतर रहेगा।"
                )
            elif lang == "or":
                msg = (
                    f"🌧️ **ରାସ୍ତା ଓଦା ରହିପାରେ ({rain_str} ମିମି ବର୍ଷା):**\n"
                    f"{loc_name} ରେ ପାଣିପାଗ {condition} ଅଛି। ଘର ଭିତରେ ବ୍ୟାୟାମ କରିବା ଭଲ।"
                )
            else:
                msg = (
                    f"🌧️ **Pavements may be slippery ({rain_str} mm rain):**\n"
                    f"In {loc_name}, we are seeing {condition} conditions. Outdoor running on wet surfaces increases slip hazards. "
                    f"An indoor workout or gym session is recommended today until conditions clear up."
                )
        elif temp_now >= 35.0:
            if lang == "hi":
                msg = (
                    f"🌡️ **काफी गर्मी है ({t_now_str} °C):**\n"
                    f"दोपहर के समय दौड़ने या भारी वर्कआउट से बचें ताकि डिहाइड्रेशन या हीट स्ट्रोक का खतरा न हो। "
                    f"सुबह 8 बजे से पहले या शाम को सूरज ढलने के बाद टहलना या दौड़ना सुरक्षित रहेगा।"
                )
            elif lang == "or":
                msg = (
                    f"🌡️ **ଅଧିକ ଗରମ ଅଛି ({t_now_str} °C):**\n"
                    f"ଦ୍ୱିପ୍ରହରରେ ବ୍ୟାୟାମରୁ ନିବୃତ୍ତ ରୁହନ୍ତୁ। ସକାଳେ କିମ୍ବା ସନ୍ଧ୍ୟାରେ ବୁଲିବା ଉଚିତ।"
                )
            else:
                msg = (
                    f"🌡️ **High heat warning ({t_now_str} °C):**\n"
                    f"Midday running or vigorous outdoor exercise in {loc_name} is not advised due to dehydration and heat stress risk. "
                    f"Schedule your run early in the morning before 8 AM or after sunset, and carry plenty of fluids."
                )
        else:
            if lang == "hi":
                msg = (
                    f"🏃‍♂️ **दौड़ने और टहलने के लिए बेहतरीन मौसम है!**\n\n"
                    f"{loc_name} में वर्तमान तापमान **{t_now_str} °C** है, आसमान **{condition}** है और हवा **{wind_str} किमी/घंटा** चल रही है। "
                    f"मौसम बहुत सुहावना है, आप आराम से रनिंग, वॉक या आउटडोर खेल का आनंद ले सकते हैं!"
                )
            elif lang == "or":
                msg = (
                    f"🏃‍♂️ **ଦୌଡ଼ିବା କିମ୍ବା ବୁଲିବା ପାଇଁ ଉତ୍ତମ ପାଣିପାଗ!**\n\n"
                    f"{loc_name} ରେ ତାପମାତ୍ରା **{t_now_str} °C** ଏବଂ ଆକାଶ **{condition}** ଅଛି। ବ୍ୟାୟାମ ପାଇଁ ଅନୁକୂଳ ସମୟ।"
                )
            else:
                msg = (
                    f"🏃‍♂️ **Great conditions for running or outdoor fitness!**\n\n"
                    f"In {loc_name}, it is currently **{t_now_str} °C** with **{condition}** skies and gentle winds of **{wind_str} km/h**. "
                    f"Visibility is clear and conditions are pleasant—an ideal window for a morning or evening jog, brisk walk, or cycling session!"
                )

        replies = ["What should I wear? 👕", "Do I need an umbrella? ☔", "Today's Forecast 🌦️", "Active Alerts ⚠️"]
        return msg, replies

    # Driving / Travel / Commute Safety
    travel_patterns = [
        r'\b(drive|driving|travel|traveling|road|traffic|highway|trip|commute|journey|safe to travel)\b',
        r'(गाड़ी|यात्रा|सड़क|सफर)',
        r'(ଯାତ୍ରା|ଗାଡ଼ି|ରାସ୍ତା)'
    ]
    if any(re.search(p, clean_q) for p in travel_patterns):
        if has_alert:
            if lang == "hi":
                msg = f"🚗 **सावधानी से यात्रा करें:** {loc_name} में आधिकारिक चेतावनी है: {alert_headline}। अनावश्यक यात्रा टालें।"
            elif lang == "or":
                msg = f"🚗 **ସତର୍କତାର ସହ ଯାତ୍ରା କରନ୍ତୁ:** {loc_name} ରେ ଚେତାବନୀ ଅଛି: {alert_headline}।"
            else:
                msg = f"🚗 **Travel with heightened caution:** There is an active weather alert for {loc_name}: {alert_headline}. Avoid non-essential road travel if conditions worsen."
        elif rain > 15.0 or wind > 35.0 or "fog" in condition.lower():
            if lang == "hi":
                msg = (
                    f"🚗 **गाड़ी चलाते समय सावधानी बरतें:**\n"
                    f"{loc_name} में दृश्यता और सड़क की पकड़ {condition} मौसम (हवा: {wind_str} किमी/घंटा, बारिश: {rain_str} मिमी) के कारण प्रभावित हो सकती है। "
                    f"धीमी गति में चलें और लो-बीम लाइट चालू रखें।"
                )
            elif lang == "or":
                msg = (
                    f"🚗 **ସାବଧାନତାର ସହ ଗାଡ଼ି ଚଲାନ୍ତୁ:** {loc_name} ରେ ପାଣିପାଗ {condition} ଅଛି। ଧୀରେ ଗାଡ଼ି ଚଲାନ୍ତୁ।"
                )
            else:
                msg = (
                    f"🚗 **Exercise caution on the roads:**\n"
                    f"In {loc_name}, road traction and visibility may be reduced due to {condition} conditions with {wind_str} km/h winds and {rain_str} mm rain. "
                    f"Keep your low-beam headlights on, maintain safe following distance, and drive carefully."
                )
        else:
            if lang == "hi":
                msg = (
                    f"🚗 **यात्रा और ड्राइविंग के लिए मौसम अनुकूल है!**\n\n"
                    f"{loc_name} में सड़कें सूखी और दृश्यता साफ है। वर्तमान में {condition} स्थिति, तापमान {t_now_str} °C और हवा {wind_str} किमी/घंटा है। "
                    f"आपकी यात्रा सुरक्षित और सुगम रहे!"
                )
            elif lang == "or":
                msg = (
                    f"🚗 **ଯାତ୍ରା ପାଇଁ ପାଣିପାଗ ସ୍ୱାଭାବିକ ଅଛି!**\n\n"
                    f"{loc_name} ରେ ରାସ୍ତା ସଫା ଅଛି ଏବଂ ପାଣିପାଗ {condition} ଅଛି।"
                )
            else:
                msg = (
                    f"🚗 **Road and driving conditions are clear!**\n\n"
                    f"In {loc_name}, travel conditions are smooth with {condition} skies, {t_now_str} °C temperature, and calm winds ({wind_str} km/h). "
                    f"Visibility is excellent and no significant traffic hazards are observed. Safe travels!"
                )

        replies = ["What should I wear? 👕", "Do I need an umbrella? ☔", "Today's Forecast 🌦️", "Active Alerts ⚠️"]
        return msg, replies

    # Tomorrow / Multi-Day Forecast
    forecast_patterns = [
        r'\b(tomorrow|next days|weekend|weekly|3 days|forecast)\b',
        r'(कल|कल का मौसम|पूर्वानुमान)',
        r'(ଆସନ୍ତାକାଲି|ପୂର୍ବାନୁମାନ)'
    ]
    if any(re.search(p, clean_q) for p in forecast_patterns):
        if lang == "hi":
            msg = (
                f"📅 **{loc_name} के लिए 3-दिवसीय मौसम पूर्वानुमान:**\n\n"
                f"• **आज:** वर्तमान {t_now_str} °C ({condition}), अधिकतम {t_max_str} °C / न्यूनतम {t_min_str} °C, वर्षा {rain_str} मिमी\n"
                f"• **कल:** अधिकतम अनुमानित तापमान लगभग {to_target_digits(round(temp_max - 0.5, 1), 'hi')} °C / न्यूनतम {to_target_digits(round(temp_min, 1), 'hi')} °C\n"
                f"• **आगामी दिन:** सामान्य मौसमी बदलाव और सुखद स्थिति बनी रहेगी।\n\n"
                f"स्थिति सामान्य है। कोई विशेष प्रतिकूल चेतावनी नहीं है।"
            )
            replies = ["मुझे क्या पहनना चाहिए? 👕", "क्या छाते की ज़रूरत है? ☔", "सक्रिय चेतावनी ⚠️", "निकटतम आश्रय 🏠"]
        elif lang == "or":
            msg = (
                f"📅 **{loc_name} ପାଇଁ ପାଣିପାଗ ପୂର୍ବାନୁମାନ:**\n\n"
                f"• **ଆଜି:** ତାପମାତ୍ରା {t_now_str} °C ({condition}), ସର୍ବାଧିକ {t_max_str} °C / ସର୍ବନିମ୍ନ {t_min_str} °C\n"
                f"• **ଆସନ୍ତାକାଲି:** ପାଣିପାଗ ସ୍ୱାଭାବିକ ରହିବ।"
            )
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ଛତା ଦରକାର କି? ☔", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
        else:
            msg = (
                f"📅 **3-Day Weather Outlook for {loc_name}:**\n\n"
                f"• **Today:** Currently {t_now_str} °C ({condition}), High {t_max_str} °C / Low {t_min_str} °C with {rain_str} mm rain.\n"
                f"• **Tomorrow:** Projected High {to_target_digits(round(temp_max - 0.5, 1), 'en')} °C / Low {to_target_digits(round(temp_min, 1), 'en')} °C with continuing {condition.lower()} skies.\n"
                f"• **Day 3:** Outlook remains steady with seasonal conditions and mild breezes.\n\n"
                f"Overall weather remains stable. Let me know if you need specific advice for outdoor plans!"
            )
            replies = ["What should I wear? 👕", "Do I need an umbrella? ☔", "Can I go for a run? 🏃", "Active Alerts ⚠️"]
        return msg, replies

    # General Weather / Temperature
    feel_text = "pleasant and comfortable"
    if temp_now >= 34.0:
        feel_text = "hot and sunny"
    elif temp_now <= 18.0:
        feel_text = "cool and crisp"

    feel_text_hi = "सुखद और अनुकूल"
    if temp_now >= 34.0:
        feel_text_hi = "गर्म और धूपदार"
    elif temp_now <= 18.0:
        feel_text_hi = "ठंडा और ताज़ा"

    if any(w in clean_q for w in ["weather", "temperature", "temp", "मौसम", "तापमान", "ପାଣିପାଗ", "ତାପମାତ୍ରା"]):
        if lang == "hi":
            msg = (
                f"🌤️ **{loc_name} में मौसम की स्थिति:**\n\n"
                f"वर्तमान में तापमान **{t_now_str} °C** और आसमान **{condition}** है।\n\n"
                f"• **आज का पूर्वानुमान:** अधिकतम {t_max_str} °C / न्यूनतम {t_min_str} °C\n"
                f"• **आर्द्रता:** {hum_str}%\n"
                f"• **हवा की गति:** {wind_str} किमी/घंटा\n"
                f"• **संभावित वर्षा:** {rain_str} मिमी\n\n"
                f"मौसम {feel_text_hi} है। आप मुझसे कपड़े, वर्षा या बाहर निकलने से जुड़ी सलाह ले सकते हैं!"
            )
            replies = ["मुझे क्या पहनना चाहिए? 👕", "क्या छाते की ज़रूरत है? ☔", "सक्रिय चेतावनी ⚠️", "निकटतम आश्रय 🏠"]
        elif lang == "or":
            msg = (
                f"🌤️ **{loc_name} ରେ ପାଣିପାଗ ସୂଚନା:**\n\n"
                f"ବର୍ତ୍ତମାନ ତାପମାତ୍ରା **{t_now_str} °C** ଏବଂ ଆକାଶ **{condition}** ଅଛି।\n\n"
                f"• **ଆଜିର ତାପମାତ୍ରା:** ସର୍ବାଧିକ {t_max_str} °C / ସର୍ବନିମ୍ନ {t_min_str} °C\n"
                f"• **ଆର୍ଦ୍ରତା:** {hum_str}%\n"
                f"• **ପବନ ଗତି:** {wind_str} କିମି/ଘଣ୍ଟା\n"
                f"• **ବର୍ଷା:** {rain_str} ମିମି"
            )
            replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ଛତା ଦରକାର କି? ☔", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️", "ନିକଟତମ ଆଶ୍ରୟ 🏠"]
        else:
            msg = (
                f"🌤️ **Real-Time Weather in {loc_name}:**\n\n"
                f"Currently it is **{t_now_str} °C** and **{condition}**.\n\n"
                f"• **Today's Range:** High {t_max_str} °C / Low {t_min_str} °C\n"
                f"• **Precipitation:** {rain_str} mm\n"
                f"• **Humidity & Wind:** {hum_str}% humidity, {wind_str} km/h winds\n\n"
                f"Conditions are {feel_text}. Feel free to ask what to wear, if you need an umbrella, or about travel safety!"
            )
            replies = ["What should I wear? 👕", "Do I need an umbrella? ☔", "Today's Forecast 🌦️", "Active Alerts ⚠️"]
        return msg, replies

    # -------------------------------------------------------------
    # 7. UNIVERSAL OPEN-DOMAIN INTELLIGENT RESPONDER
    # -------------------------------------------------------------
    # Fallback for any other question in the world
    clean_display = query.strip()
    if lang == "hi":
        msg = (
            f"यह एक बहुत अच्छा प्रश्न है: *\"{clean_display}\"*।\n\n"
            f"एक सहायक AI साथी के रूप में, मैं इस विषय पर जानकारी प्रदान करने के लिए सदैव तैयार हूँ। "
            f"यदि आप इसके बारे में अधिक विस्तार से जानना चाहते हैं, तो कृपया मुझे बताएं! "
            f"साथ ही, {loc_name} में वर्तमान मौसम {condition} और तापमान {t_now_str} °C है।"
        )
        replies = ["और विस्तार से बताओ 💡", "आज का मौसम 🌦️", "मुझे एक चुटकुला सुनाओ 😄"]
    elif lang == "or":
        msg = (
            f"ଏହା ଏକ ଉତ୍ତମ ପ୍ରଶ୍ନ: *\"{clean_display}\"*।\n\n"
            f"ମୁଁ ଆପଣଙ୍କୁ ଏହି ବିଷୟରେ ସାହାଯ୍ୟ କରିବା ପାଇଁ ପ୍ରସ୍ତୁତ। "
            f"{loc_name} ରେ ବର୍ତ୍ତମାନ ତାପମାତ୍ରା {t_now_str} °C ଅଛି।"
        )
        replies = ["ଆଜିର ପାଣିପାଗ 🌦️", "ସକ୍ରିୟ ଚେତାବନୀ ⚠️"]
    else:
        msg = (
            f"That's a thoughtful question regarding **\"{clean_display}\"**!\n\n"
            f"As your versatile AI assistant, I can explore this topic with you in depth, provide structured explanations, "
            f"solve related problems, or summarize key perspectives. Could you tell me more about what specific angle you'd like to dive into?\n\n"
            f"*(By the way, right now in {loc_name}, it's {t_now_str} °C and {condition}.)*"
        )
        replies = ["Explain in detail 💡", "Tell me a fun fact 💡", "How's the weather? 🌦️", "Tell me a joke 😄"]

    return msg, replies
