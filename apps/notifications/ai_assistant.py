"""
AI Assistant for MediQueue support chat.
Works in two modes:
1. RULE-BASED (default, no API key needed) — FAQ matching
2. AI-POWERED (when ANTHROPIC_API_KEY is set in .env) — Claude API
"""
import re
from django.conf import settings

FAQ_RESPONSES = [
    (r'book|appointment|schedule', 
     "To book an appointment: go to 'Book Appointment', describe your symptoms, choose a hospital, and submit. A receptionist will propose a doctor and time slot for you to accept."),
    (r'payment|pay|fee|booking fee',
     "After your appointment slot is accepted, you'll be asked to pay a booking fee. We support cards, mobile money (MTN, M-Pesa, Airtel, Orange), bank transfer, and cash at the hospital."),
    (r'cancel',
     "You can cancel a pending or proposed appointment from 'My Appointments' before it's confirmed. Once confirmed, please contact the hospital directly."),
    (r'report|prescription|diagnosis',
     "Your medical reports appear under 'Medical Reports' once your doctor completes and shares them. You can download a PDF copy anytime."),
    (r'register|sign up|account',
     "To register, click 'Sign Up' on the homepage. Hospitals can register via 'Register Your Hospital' — applications are reviewed within 24-48 hours."),
    (r'password|forgot|reset',
     "Click 'Forgot Password' on the login page and follow the instructions sent to your email."),
    (r'doctor|specialist|specialization',
     "Browse hospitals and their available doctors from the 'Book Appointment' page. Each doctor's profile shows their specialization, experience, and patient ratings."),
    (r'hello|hi|hey',
     "Hi there! 👋 I'm the MediQueue assistant. Ask me about booking appointments, payments, medical reports, or your account."),
]

DEFAULT_RESPONSE = (
    "I'm not sure about that yet, but our support team can help! "
    "You can also browse our Help Center or contact your hospital directly "
    "through the appointment details page."
)


def get_ai_response(message: str, user=None) -> str:
    """Returns a chatbot response. Tries AI API if configured, else rule-based."""
    message_lower = message.lower().strip()

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if api_key:
        try:
            return _get_claude_response(message, user, api_key)
        except Exception:
            pass  # fall back to rules

    for pattern, response in FAQ_RESPONSES:
        if re.search(pattern, message_lower):
            return response

    return DEFAULT_RESPONSE


def _get_claude_response(message: str, user, api_key: str) -> str:
    import requests
    system_prompt = (
        "You are the MediQueue support assistant — a healthcare appointment "
        "platform connecting patients with hospitals in Africa. Be concise, "
        "friendly, and helpful. Answer questions about booking appointments, "
        "payments, medical reports, and account management. If asked about "
        "specific medical advice, politely redirect to consult their doctor. "
        "Keep responses under 100 words."
    )
    user_context = ''
    if user and user.is_authenticated:
        user_context = f' The user is logged in as a {user.role}.'

    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        },
        json={
            'model': 'claude-sonnet-4-6',
            'max_tokens': 200,
            'system': system_prompt + user_context,
            'messages': [{'role': 'user', 'content': message}],
        },
        timeout=15,
    )
    data = resp.json()
    return data['content'][0]['text']