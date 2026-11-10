"""
AI Service — Google Gemini Integration
Provides the security analyst chatbot powered by Gemini 1.5 Pro.
System prompt is crafted to make Gemini behave as an expert SOC analyst.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CyberSentinel AI, an elite cybersecurity analyst and SOC (Security Operations Center) expert. 
You are embedded within a professional cybersecurity SaaS platform used by security teams.

Your capabilities include:
- Analyzing security alerts, logs, and threat indicators
- Explaining attack techniques using MITRE ATT&CK framework
- Providing actionable incident response guidance
- CVE analysis and vulnerability risk assessment
- Threat hunting hypothesis generation
- Malware behavior analysis
- Network traffic anomaly explanation
- Compliance and regulatory guidance (SOC 2, ISO 27001, NIST, CIS Controls)

Rules:
1. Always respond with precise, technical, actionable information
2. Reference MITRE ATT&CK tactics/techniques when relevant (e.g., T1059 - Command Scripting Interpreter)
3. Provide severity context and recommended immediate actions
4. Never provide information that could enable attacks or harm systems
5. If a context (alert ID, threat indicator, log entry) is provided, analyze it specifically
6. Format responses with clear sections when appropriate
7. Be concise but complete — security teams are busy

Always think from a defensive security perspective."""


async def get_ai_response(
    user_message: str,
    history: list[dict],
    context_type: str = "general",
    context_ref_id: Optional[str] = None,
) -> tuple[str, Optional[int]]:
    """
    Sends a message to the Gemini API and returns the response text and token count.
    Falls back gracefully if the API key is not configured.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key not configured — returning demo response.")
        return _demo_response(user_message), None

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.3,       # Lower temp for factual security responses
                "max_output_tokens": 2048,
                "top_p": 0.95,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            ],
        )

        # Build conversation history for multi-turn chat
        chat = model.start_chat(
            history=[
                {"role": msg["role"], "parts": [msg["content"]]}
                for msg in history
                if msg["role"] in ("user", "model")
            ]
        )

        # Add context prefix if available
        full_message = user_message
        if context_type != "general" and context_ref_id:
            full_message = f"[Context: {context_type} ID={context_ref_id}]\n\n{user_message}"

        response = await chat.send_message_async(full_message)

        tokens_used = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_used = response.usage_metadata.total_token_count

        return response.text, tokens_used

    except Exception as e:
        logger.error("Gemini API error: %s", e)
        return (
            "I apologize, I'm temporarily unable to process your request due to an AI service error. "
            "Please try again in a moment, or contact your administrator if the issue persists.",
            None,
        )


def _demo_response(message: str) -> str:
    """Returns a structured demo response when no API key is configured."""
    return (
        "⚠️ **AI Analyst is in Demo Mode** — Gemini API key not configured.\n\n"
        f"Your query: *{message[:200]}*\n\n"
        "**To enable the AI Analyst:**\n"
        "1. Obtain a Gemini API key from Google AI Studio (aistudio.google.com)\n"
        "2. Add `GEMINI_API_KEY=your_key_here` to your `.env` file\n"
        "3. Restart the backend service\n\n"
        "Once configured, I can analyze threats, explain alerts, suggest remediation steps, "
        "and assist with incident response using MITRE ATT&CK framework."
    )
