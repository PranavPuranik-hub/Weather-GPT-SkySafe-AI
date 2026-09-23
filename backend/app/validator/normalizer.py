"""
Normalizer for Indic digits and Hindi/English number words.
"""
import re

INDIC_DIGITS_MAP = {
    # Devanagari (Hindi, Marathi, etc.)
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    # Bengali
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
    # Gujarati
    '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4',
    '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    # Gurmukhi (Punjabi)
    '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4',
    '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',
    # Odia
    '୦': '0', '୧': '1', '୨': '2', '୩': '3', '୪': '4',
    '୫': '5', '୬': '6', '୭': '7', '୮': '8', '୯': '9',
    # Tamil
    '௦': '0', '௧': '1', '௨': '2', '௩': '3', '௪': '4',
    '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',
    # Telugu
    '౦': '0', '౧': '1', '౨': '2', '౩': '3', '౪': '4',
    '౫': '5', '౬': '6', '౭': '7', '౮': '8', '౯': '9',
    # Kannada
    '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4',
    '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
    # Malayalam
    '൦': '0', '൧': '1', '൨': '2', '൩': '3', '൪': '4',
    '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9',
    # Urdu/Arabic
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    # Persian
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}

NUMBER_WORDS_MAP = {
    # English
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "twenty": "20",
    "thirty": "30", "forty": "40", "fifty": "50", "sixty": "60",
    "seventy": "70", "eighty": "80", "ninety": "90", "hundred": "100",

    # Hindi
    "शून्य": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
    "पांच": "5", "छह": "6", "छः": "6", "सात": "7", "आठ": "8", "नौ": "9",
    "दस": "10", "ग्यारह": "11", "बारह": "12", "बीस": "20", "तीस": "30",
    "चालीस": "40", "पचास": "50", "साठ": "60", "सत्तर": "70", "अस्सी": "80",
    "नब्बे": "90", "सौ": "100"
}

def normalize_indic_digits(text: str) -> str:
    """Replace all Indic digits with ASCII digits."""
    return ''.join(INDIC_DIGITS_MAP.get(char, char) for char in text)

def normalize_number_words(text: str) -> str:
    """
    Replace number words in text with their digit representations.
    This is a basic token-wise replacement.
    """
    words = text.split()
    normalized_words = []

    for word in words:
        clean_word = re.sub(r'[^\w\s]', '', word).lower()
        if clean_word in NUMBER_WORDS_MAP:
            # Replace while trying to preserve attached punctuation
            val = NUMBER_WORDS_MAP[clean_word]
            # Replace the word with the digit, keeping punctuation
            word = re.sub(r'(?i)\b' + re.escape(clean_word) + r'\b', val, word)
        normalized_words.append(word)

    return " ".join(normalized_words)

def normalize_text_for_numbers(text: str) -> str:
    text = normalize_indic_digits(text)
    text = normalize_number_words(text)
    return text
