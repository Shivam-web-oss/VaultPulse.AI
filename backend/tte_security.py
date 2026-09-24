import re
import hashlib
from typing import Tuple, Dict

class TTESecurityVault:
    """
    Simulates a Trusted Execution Environment (TTE) pipeline:
    1. Redacts sensitive information (PII, tokens, emails, phone numbers) locally.
    2. Maps original sensitive tokens to isolated enclave hashes.
    3. Re-hydrates response safely after processing.
    """
    def __init__(self):
        self._enclave_vault: Dict[str, str] = {}

    def secure_payload(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Removes sensitive identifiers before transmitting to external AI."""
        sanitized_text = text
        local_mappings = {}

        # 1. Detect & Redact Emails
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = re.findall(email_pattern, text)
        for email in emails:
            token = f"[SECURE_EMAIL_{hashlib.md5(email.encode()).hexdigest()[:6]}]"
            sanitized_text = sanitized_text.replace(email, token)
            local_mappings[token] = email

        # 2. Detect & Redact Phone Numbers
        phone_pattern = r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        phones = re.findall(phone_pattern, text)
        for phone in phones:
            if len(phone.strip()) >= 7:
                token = f"[SECURE_PHONE_{hashlib.md5(phone.encode()).hexdigest()[:6]}]"
                sanitized_text = sanitized_text.replace(phone, token)
                local_mappings[token] = phone

        # 3. Detect & Redact Credentials / API Keys
        cred_pattern = r'(?i)(api[_-]?key|secret|bearer)\s*[:=]\s*([a-zA-Z0-9_\-]+)'
        matches = re.findall(cred_pattern, text)
        for match in matches:
            secret_val = match[1]
            token = f"[SECURE_CREDENTIAL_{hashlib.md5(secret_val.encode()).hexdigest()[:6]}]"
            sanitized_text = sanitized_text.replace(secret_val, token)
            local_mappings[token] = secret_val

        return sanitized_text, local_mappings

    def restore_payload(self, ai_response: str, local_mappings: Dict[str, str]) -> str:
        """Restores encrypted tokens back into original readable form inside local memory."""
        restored_text = ai_response
        for token, original in local_mappings.items():
            restored_text = restored_text.replace(token, original)
        return restored_text

# Global instance imported by main.py
tte_vault = TTESecurityVault()