from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def get_fernet():
    key = settings.MESSAGE_ENCRYPTION_KEY

    if not key:
        raise ValueError("MESSAGE_ENCRYPTION_KEY is missing from settings/.env")

    return Fernet(key.encode())


def encrypt_message_text(text):
    if not text:
        return text

    fernet = get_fernet()
    encrypted_text = fernet.encrypt(text.encode())
    return encrypted_text.decode()


def decrypt_message_text(encrypted_text):
    if not encrypted_text:
        return encrypted_text

    try:
        fernet = get_fernet()
        decrypted_text = fernet.decrypt(encrypted_text.encode())
        return decrypted_text.decode()
    except InvalidToken:
        # For old messages that were saved before encryption
        return encrypted_text