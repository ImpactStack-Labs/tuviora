import json
import os

from openai import OpenAI


class AIServiceError(Exception):
    """Raised when the AI feedback analysis service fails."""


def analyze_feedback(feedback_items):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is not configured.")

    if not feedback_items:
        return {
            "themes": [],
            "concerns_summary": "",
            "suggested_improvements": [],
        }

    feedback_text = "\n\n".join(
        [
            (
                f"Rating: {feedback.rating or 'Not provided'}\n"
                f"Comment: {feedback.comment}"
            )
            for feedback in feedback_items
        ]
    )

    prompt = f"""
You are an attendee feedback analysis assistant for an event management platform.

Analyze the following attendee feedback and return ONLY valid JSON.

Important:
- Your output is AI-generated analysis, not direct attendee statements.
- Identify recurring themes based only on the feedback provided.
- Summarize attendee concerns without inventing information.
- Suggest practical improvements for the organizer based only on the feedback.
- Do not invent facts, feedback, ratings, or problems that are not present.
- If feedback contains conflicting opinions, reflect that uncertainty.
- Do not identify individual attendees.
- Do not claim that suggested improvements have already been implemented.

Attendee feedback:
{feedback_text}

Return JSON in exactly this structure:
{{
    "themes": [
        {{
            "theme": "short recurring theme",
            "description": "brief explanation of the theme",
            "frequency": 1
        }}
    ],
    "concerns_summary": "concise summary of attendee concerns",
    "suggested_improvements": [
        "practical improvement 1",
        "practical improvement 2"
    ]
}}
"""

    try:
        client = OpenAI(api_key=api_key)

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
        "themes",
        "concerns_summary",
        "suggested_improvements",
    }

    if not required_fields.issubset(result):
        raise AIServiceError(
            "AI service response is missing required fields."
        )

    if not isinstance(result["themes"], list):
        raise AIServiceError(
            "AI service returned invalid themes."
        )

    if not isinstance(result["suggested_improvements"], list):
        raise AIServiceError(
            "AI service returned invalid suggested improvements."
        )

    if not isinstance(result["concerns_summary"], str):
        raise AIServiceError(
            "AI service returned an invalid concerns summary."
        )

    return result
