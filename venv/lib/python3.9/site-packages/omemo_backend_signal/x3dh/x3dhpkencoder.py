from __future__ import absolute_import

import omemo

class X3DHPKEncoder(omemo.backends.X3DHPKEncoder):
    @staticmethod
    def encodePublicKey(key, key_type):
        if key_type == "25519":
            return b"\x05" + key

        raise NotImplementedError

    @staticmethod
    def decodePublicKey(key_encoded):
        if key_encoded[0:1] == b"\x05":
            return (key_encoded[1:], "25519")
        
        raise NotImplementedError
