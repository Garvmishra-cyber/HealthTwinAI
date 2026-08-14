import os
from openai import OpenAI


# =========================================================
# OPENAI CONFIG
# =========================================================

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not available."
    )


client = OpenAI(
    api_key=api_key
)


# =========================================================
# HEALTH AI
# =========================================================

def ask_health_ai(
    user_message,
    report_context=""
):

    system_prompt = """
You are HealthTwin AI.

You are an educational health-information assistant
inside a medical report analysis application.

Your job is to explain the user's uploaded report
in simple and understandable language.

Rules:

1. Do not diagnose diseases.
2. Do not claim certainty about medical conditions.
3. Do not replace a doctor or healthcare professional.
4. Do not invent report values.
5. Use the provided report context when answering.
6. If a value is unavailable, say that it is unavailable.
7. Explain medical terms simply.
8. Do not recommend changing prescribed medication doses.
9. When discussing normal or abnormal values, remind the
   user that laboratory reference ranges can vary.
10. Keep answers concise and useful.

This is an educational assistant, not a diagnostic system.
"""

    user_prompt = f"""
LATEST USER REPORT:

{report_context}


USER QUESTION:

{user_message}
"""

    try:

        response = client.responses.create(

            model="gpt-5-mini",

            instructions=system_prompt,

            input=user_prompt,

            max_output_tokens=500

        )

        answer = response.output_text

        if not answer:

            return (
                "AI returned an empty response. "
                "Please try again."
            )

        return answer.strip()

    except Exception as error:

        # -------------------------------------------------
        # PRINT REAL ERROR IN TERMINAL
        # -------------------------------------------------

        print("\n" + "=" * 70)

        print("OPENAI API ERROR")

        print("=" * 70)

        print(type(error).__name__)

        print(str(error))

        print("=" * 70 + "\n")

        return (
            "Sorry, I couldn't connect to the AI service "
            "right now. Please try again."
        )