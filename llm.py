# llm.py
import os
import json
from typing import Optional, Dict, Any

# Note: google.generativeai is configured from app.py via configure_genai()
import google.generativeai as genai


# ---------------------------
# Public configure function
# ---------------------------
def configure_genai(api_key: str) -> None:
    """
    Configure the google-generativeai SDK with the provided API key.
    Call this once from app.py AFTER loading .env.
    """
    if not api_key:
        raise ValueError("API key required for configure_genai()")
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key
    genai.configure(api_key=api_key)


# ---------------------------
# Prompt templates
# ---------------------------
SYSTEM_PROMPT = """You are NyaySathi, an Indian legal assistant. The user will provide a plain-language description of their legal issue.

Return a single JSON object ONLY with fields:
- case_type: short label (e.g., domestic_violence, cybercrime, consumer)
- severity: integer (1-10)
- short_summary: single-sentence summary
- relevant_laws: list of objects {section: "IPC 498A", brief: "short explanation"}
- documents_needed: list of strings
- drafts: object with keys like:
    - FIR_email: A properly formatted email/FIR draft with correct newlines ("\n") and blank lines between sections.
      MUST follow this structure (example) exactly:
      
      To,
      The Station House Officer
      [Police Station Name],
      [City Name]

      Subject: [Subject]

      Respected Sir/Madam,

      [Body paragraph 1]

      [Body paragraph 2]

      Thanking you,
      Yours faithfully,
      [Your Name]
      [Contact Number]
      [Date]

    - legal_notice: A properly formatted legal notice or formal letter with paragraph breaks.

- action_plan: ordered list of steps (strings)
- evidence_checklist: list of strings
- presentation_markdown: a concise human-friendly markdown (max ~300 words) summarizing advice

Important:
- Return ONLY valid JSON (no surrounding commentary).
- Ensure strings include newline characters where appropriate (e.g., in FIR_email).
"""

INSTRUCTION_PROMPT = """
User description:
{user_text}

User interface language: {lang}
Anonymous mode: {anon}
Location hint: {location}
display_language: {lang}
"""


def build_prompt(user_text: str, lang: str, anon: bool, location: str) -> str:
    """
    Build the full prompt sent to the LLM.
    """
    return SYSTEM_PROMPT + "\n\n" + INSTRUCTION_PROMPT.format(
        user_text=user_text, lang=lang, anon=str(anon), location=location or "unknown"
    )


# ---------------------------
# Model call & response helpers
# ---------------------------

# Your current API is v1beta, which supports gemini-pro; 1.5 models are giving 404.
DEFAULT_MODEL = "gemini-2.5-flash"


def call_gemini(prompt: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Call Gemini using the google-generativeai SDK.
    Returns the raw text (string) the model produced (best-effort).
    """
    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)

        # SDK v1: resp.text exists for text models
        if hasattr(resp, "text") and resp.text:
            return resp.text

        # Some SDK responses are dict-like (defensive handling)
        if isinstance(resp, dict):
            cands = resp.get("candidates") or resp.get("outputs") or []
            if isinstance(cands, list) and len(cands) > 0:
                first = cands[0]
                for k in ("content", "text", "output"):
                    if isinstance(first, dict) and first.get(k):
                        return first.get(k)

            out = resp.get("output")
            if isinstance(out, str):
                return out

            return json.dumps(resp)

        # Fallback: string conversion
        return str(resp)

    except Exception as e:
        # Always return a JSON string so the app can display the error
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


def extract_json_from_text(s: str) -> Optional[Dict[str, Any]]:
    """
    Try to extract a JSON object from model output text.
    Returns parsed dict or None if parsing fails.
    """
    if not s:
        return None

    s = s.strip()

    # Direct attempt
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try extracting {...}
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end >= start:
        candidate = s[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            try:
                cleaned = candidate.replace("\n", " ").replace("'", '"')
                return json.loads(cleaned)
            except Exception:
                return None

    return None
