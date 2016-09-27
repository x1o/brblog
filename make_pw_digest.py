from hashlib import sha256
from base64 import b64encode

def make_pw_digest(plain):
    return b64encode(sha256(plain).digest())

while True:
    resp = raw_input('Enter your passphrase: ')
    if resp:
        print make_pw_digest(resp)
        break
