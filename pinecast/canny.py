import binascii
import hashlib
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from django.conf import settings

from .helpers import gravatar


def get_canny_token(req):
    if not req.user:
        return None

    user_data = {
        'avatarURL': gravatar(req.user.email),
        'email': req.user.email,
        'id': req.user.id,
        'name': req.user.email,
    }
    plaintext = json.dumps(user_data)

    dig = hashlib.md5(settings.CANNY_SSO_KEY.encode('utf-8')).digest()
    cipher = Cipher(algorithms.AES(dig), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()

    padding_required = 16 - len(plaintext) % 16
    if padding_required != 16:
        encoded = plaintext.encode('utf-8') + padding_required * bytes([padding_required])

    ciphertext = encryptor.update(encoded) + encryptor.finalize()
    return binascii.hexlify(ciphertext).decode('utf-8')
