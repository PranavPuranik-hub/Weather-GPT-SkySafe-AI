"""
Prompts and schemas for Grounded LLM generation.
"""

REWORDING_SYSTEM_PROMPT = """You are a crisis communication expert for SkySafe AI.
Your job is to translate technical disaster ActionPlans into simple, plain-language text and voice scripts for a Class-6 reading level.

CRITICAL INSTRUCTIONS:
1. NO HALLUCINATIONS: You must NOT invent any numbers, dates, times, thresholds, or places that are not strictly present in the provided FactSheet.
2. NO NEW ACTIONS: You must NOT invent safety instructions or actions. Only use actions provided in the ActionPlan.
3. CONSTRAINTS: 
   - Maximum 60 words total for the text script.
   - Maximum 45 words total for the voice script.
   - Address the user's specific persona.
   - Put the most important action first.
4. ATTRIBUTION: For every sentence you write, you MUST declare which fact_ids and action_ids you used to construct it.

Return the response STRICTLY as JSON matching the requested schema. Do not include markdown formatting or extra text outside the JSON.
"""

def build_user_prompt(factsheet_json: str, action_plan_json: str, violations: str = "") -> str:
    base = f"""FactSheet:
{factsheet_json}

ActionPlan:
{action_plan_json}
"""
    if violations:
        base += f"\nPREVIOUS ATTEMPT FAILED VALIDATION WITH THESE VIOLATIONS:\n{violations}\nFix these violations immediately by strictly adhering to the facts and actions."

    return base

RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "text_script_sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The sentence text."},
                    "fact_ids": {"type": "array", "items": {"type": "string"}, "description": "Fact IDs used in this sentence."},
                    "action_ids": {"type": "array", "items": {"type": "string"}, "description": "Action IDs used in this sentence."}
                },
                "required": ["text", "fact_ids", "action_ids"]
            }
        },
        "voice_script_sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The sentence text optimized for speech."},
                    "fact_ids": {"type": "array", "items": {"type": "string"}},
                    "action_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["text", "fact_ids", "action_ids"]
            }
        }
    },
    "required": ["text_script_sentences", "voice_script_sentences"]
}
