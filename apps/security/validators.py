"""
Input validation and sanitization for MediQueue.
CIA — Integrity: ensures only clean data enters the system.
"""
import re
import os
from django.core.exceptions import ValidationError


# ── File Upload Security ──────────────────────────────────────

ALLOWED_IMAGE_TYPES    = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
ALLOWED_DOCUMENT_TYPES = {'application/pdf', 'image/jpeg', 'image/png'}
ALLOWED_PAYMENT_PROOF  = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}

MAX_UPLOAD_SIZE_MB = 10  # 10MB


def validate_clinic_document(file):
    """Validates uploaded clinic registration documents."""
    _validate_file_size(file, max_mb=10)
    _validate_file_type(file, ALLOWED_DOCUMENT_TYPES, 'document')
    _validate_file_extension(file, {'.pdf', '.jpg', '.jpeg', '.png'})
    _scan_filename(file.name)


def validate_payment_proof(file):
    """Validates uploaded payment proof files."""
    _validate_file_size(file, max_mb=5)
    _validate_file_type(file, ALLOWED_PAYMENT_PROOF, 'payment proof')
    _validate_file_extension(file, {'.pdf', '.jpg', '.jpeg', '.png', '.webp'})
    _scan_filename(file.name)


def validate_profile_photo(file):
    """Validates profile photo uploads."""
    _validate_file_size(file, max_mb=5)
    _validate_file_type(file, ALLOWED_IMAGE_TYPES, 'image')
    _validate_file_extension(file, {'.jpg', '.jpeg', '.png', '.gif', '.webp'})
    _scan_filename(file.name)


def _validate_file_size(file, max_mb: int):
    size_mb = file.size / (1024 * 1024)
    if size_mb > max_mb:
        raise ValidationError(f'File too large. Maximum size is {max_mb}MB. Your file is {size_mb:.1f}MB.')


def _validate_file_type(file, allowed_types: set, file_description: str):
    import magic  # pip install python-magic-bin (Windows)
    try:
        file_type = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        if file_type not in allowed_types:
            raise ValidationError(
                f'Invalid {file_description} type: {file_type}. '
                f'Allowed: {", ".join(allowed_types)}'
            )
    except ImportError:
        # If python-magic not installed, fall back to extension check only
        pass


def _validate_file_extension(file, allowed_extensions: set):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'File extension "{ext}" not allowed. '
            f'Allowed: {", ".join(allowed_extensions)}'
        )


def _scan_filename(filename: str):
    """Prevent path traversal in filenames."""
    dangerous = ['..', '/', '\\', '\x00', '\n', '\r']
    for d in dangerous:
        if d in filename:
            raise ValidationError('Invalid file name.')


# ── Input Sanitization ────────────────────────────────────────

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Remove dangerous characters from text input."""
    if not text:
        return ''
    # Remove null bytes
    text = text.replace('\x00', '')
    # Limit length
    text = text[:max_length]
    return text.strip()


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    return clean.isdigit() and 7 <= len(clean) <= 15


def validate_strong_password(password: str) -> list:
    """Returns list of errors. Empty list = valid."""
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password must contain at least one special character.')
    return errors


def validate_card_number(number: str) -> bool:
    """Luhn algorithm card validation."""
    digits = number.replace(' ', '').replace('-', '')
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0