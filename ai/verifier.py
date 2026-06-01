import json
import requests

from config import OLLAMA_BASE_URL, LOCAL_TEXT_MODEL


VERIFICATION_SCHEMA_DESCRIPTION = """

Return a JSON object like:

{
    "issues": [
        {
            "field": "field_name",
            "problem": "description",
            "suggestion": "better value or null",
            "severity" : "error|warning|info"
        }
    ],
    
    "corrected_fields": {
        "field_name" : "value or null"
    },
    "overall_confidence": "high|medium|low",
    "ready_for_review": true
}

Rules:
- steur_id shoudl have 11 digits if present
- BIC should be 8 or 11 characters long if present
- date_of_birth should be in the format DD.MM.YYYY
- place_of_birth must not be confused with current city.
- do not invent missing data
"""

class LocalOllamaVerifier:
    def __init__(self, model_name: str= LOCAL_TEXT_MODEL):
        self.model_name = model_name
        
    def verify_extraction(self, original_text: str, extracted: dict) -> dict:
        prompt = f"""
        
        Yor are a multilingual employee data verification system. 
        
        Task:
        Check the extracted employee data against the original text.
        Return JSON only.
        
        Schema:
        {VERIFICATION_SCHEMA_DESCRIPTION}
        
        Original Text:
        {original_text[:6000]}
        
        Extracted Data:
        {json.dumps(extracted, ensure_ascii= False)}
        
        """
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format":"json",
            },
            timeout=None,
        )
        response.raise_for_status()
        result = response.json()
        text = result.get("response", "").strip()
        
        return json.loads(text)
    
