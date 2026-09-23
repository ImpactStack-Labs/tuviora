import json
import os

from openai import OpenAI


class AIServiceError(Exception):
    """Raised when the AI incident analysis service fails."""


def analyze_incident(incident):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an incident analysis assistant for an event management platform.

Analyze the following incident and return ONLY valid JSON.

Important:
- Your output is a recommendation, not a verified fact.
- Do not invent information that is not present in the incident.
- Suggested severity and priority are recommendations for the organizer.
- Recommended actions must be practical and directly related to the incident.
- The draft message must be suitable for attendees.
- Do not claim that a message has been sent.

Incident:
Title: {incident.title}
Description: {incident.description}
Category: {incident.category}
Current Severity: {incident.severity}
Status: {incident.status}
Event: {incident.event.name}

Return JSON in exactly this structure:
{{
    "classification": "short incident classification",
    "suggested_severity": "low|medium|high|critical",
    "priority": "low|medium|high|urgent",
    "recommended_actions": [
        "action 1",
        "action 2",
        "action 3"
    ],
    "draft_message": "draft attendee communication"
}}
"""

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=prompt,
        )
    except Exception as exc:
        raise AIServiceError(
            f"AI service request failed: {exc}"
        ) from exc

    try:
        result = json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AIServiceError(
            "AI service returned an invalid JSON response."
        ) from exc

    required_fields = {
        "classification",
        "suggested_severity",
        "priority",
        "recommended_actions",
        "draft_message",
    }

    if not required_fields.issubset(result):
        raise AIServiceError(
            "AI service response is missing required fields."
        )

    return result
