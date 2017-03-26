import binascii
import hashlib
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from django.conf import settings

from .helpers import gravatar


ADJECTIVES = {
    '0': 'Ancient',
    '1': 'Breezy',
    '2': 'Charming',
    '3': 'Delightful',
    '4': 'Exuberant',
    '5': 'Fantastic',
    '6': 'Jolly',
    '7': 'Lively',
    '8': 'Magnificent',
    '9': 'Outrageous',
    'A': 'Pleasant',
    'B': 'Robust',
    'C': 'Splendid',
    'D': 'Thoughtful',
    'E': 'Victorious',
    'F': 'Zany',
}
NOUNS = {
    '0': 'Piccolo',
    '1': 'Toaster',
    '2': 'Sandwich',
    '3': 'Traveler',
    '4': 'Dragon',
    '5': 'Ninja',
    '6': 'Superhero',
    '7': 'Rainbow',
    '8': 'Suitcase',
    '9': 'Alligator',
    'A': 'Isotope',
    'B': 'Asymptote',
    'C': 'Compiler',
    'D': 'Soup',
    'E': 'Droid',
    'F': 'Constellation',
}


def get_anonymous_name(email):
    h = hashlib.md5(email.encode('utf-8')).hexdigest()
    return 'Anonymous %s %s' % (ADJECTIVES[h[0].upper()], NOUNS[h[1].upper()])


def get_canny_token(req):
    if not req.user:
        return None

    user_data = {
        'avatarURL': gravatar(req.user.email),
        'email': req.user.email,
        'id': req.user.id,
        'name': get_anonymous_name(req.user.email),
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
