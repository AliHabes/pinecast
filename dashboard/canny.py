import codecs
import hashlib
import json

import pyaes
from django.conf import settings

from pinecast.helpers import gravatar


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
    aes = pyaes.AESModeOfOperationECB(dig)

    ciphertext = b''
    for i in range(0, len(plaintext), 16):
        ciphertext += aes.encrypt(plaintext[i:16].rjust(16))

    return codecs.encode(ciphertext, 'hex_codec').decode('utf-8')
