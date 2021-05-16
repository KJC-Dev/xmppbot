from __future__ import absolute_import

import copy
import hashlib
import os

from ..xeddsa import XEdDSA

from .ref10 import *

from nacl.exceptions import BadSignatureError
from nacl.public import PrivateKey as Curve25519DecryptionKey
from nacl.signing import VerifyKey as Ed25519VerificationKey

class XEdDSA25519(XEdDSA):
    """
    An implementation of XEdDSA for Montgomery Curve25519 and Twisted Edwards Ed25519
    keys.
    """

    MONT_PRIV_KEY_SIZE = 32
    MONT_PUB_KEY_SIZE  = 32
    ED_PRIV_KEY_SIZE   = 32
    ED_PUB_KEY_SIZE    = 32
    SIGNATURE_SIZE     = 64

    @staticmethod
    def _generate_mont_priv():
        priv = bytearray(os.urandom(32))

        # The following step is referred to as "clamping".
        # The following links to a mailing list discussion about what clamping does:
        # https://moderncrypto.org/mail-archive/curves/2017/000858.html

        # I am not sure why, but without clamping XEdDSA does not work.
        # Maybe the ref10 implementation expects all scalars to be clamped.
        priv[0]  &= 248
        priv[31] &=  63
        priv[31] |=  64

        return priv

    @staticmethod
    def _mont_pub_from_mont_priv(mont_priv):
        mont_priv_bytes = bytes(mont_priv)
        mont_pub_bytes  = bytes(Curve25519DecryptionKey(mont_priv_bytes).public_key)

        return bytearray(mont_pub_bytes)

    @staticmethod
    def _mont_priv_to_ed_pair(mont_priv):
        # Prepare a buffer for the twisted Edwards private key
        ed_priv = copy.deepcopy(mont_priv)

        # Get the twisted edwards public key, including the sign bit
        ed_pub = ge_p3_tobytes(ge_scalarmult_base(mont_priv))

        # Save the sign bit for later
        sign_bit = (ed_pub[31] >> 7) & 1

        # Force the sign bit to zero
        ed_pub[31] &= 0x7F

        # Prepare the negated private key
        ed_priv_neg = sc_neg(ed_priv)

        # Get the correct private key based on the sign stored above
        sc_cmov(ed_priv, ed_priv_neg, sign_bit)

        return ed_priv, ed_pub

    @staticmethod
    def _mont_pub_to_ed_pub(mont_pub):
        # Read the public key as a field element
        mont_pub = fe_frombytes(mont_pub)

        # Convert the Montgomery public key to a twisted Edwards public key
        fe_ONE = fe_1()

        # Calculate the parameters (u - 1) and (u + 1)
        mont_pub_minus_one = fe_sub(mont_pub, fe_ONE)
        mont_pub_plus_one  = fe_add(mont_pub, fe_ONE)

        # Prepare inv(u + 1)
        mont_pub_plus_one = fe_invert(mont_pub_plus_one)

        # Calculate y = (u - 1) * inv(u + 1) (mod p)
        ed_pub = fe_mul(mont_pub_minus_one, mont_pub_plus_one)
        ed_pub = fe_tobytes(ed_pub)

        return ed_pub

    @staticmethod
    def _sign(data, nonce, ed_priv, ed_pub):
        # Aliases for consistency with the specification
        M = data
        Z = nonce

        # A, a = calculate_key_pair(k)
        A = ed_pub
        a = ed_priv

        # r = hash_1(a || M || Z) (mod q)

        # If the hash has an index as above, that means, we are supposed to calculate:
        #     hash(2 ^ b - 1 - i || X)
        #
        # If b = 256 (which is the case for 25519 XEdDSA), then 2 ^ b - 1 = [ 0xFF ] * 32
        # Now, subtracting i from the result can be done by subtracting i from the first
        # byte (assuming i <= 0xFF).
        padding = bytearray(b"\xFF" * 32)
        padding[0] -= 1
        r = bytearray(hashlib.sha512(bytes(padding + a + M + Z)).digest())
        r = sc_reduce(r)

        # R = rB
        R = ge_p3_tobytes(ge_scalarmult_base(r))

        # h = hash(R || A || M) (mod q)
        h = bytearray(hashlib.sha512(bytes(R + A + M)).digest())
        h = sc_reduce(h)

        # s = r + ha (mod q)
        s = sc_muladd(h, a, r)

        return R + s

    @staticmethod
    def _verify(data, signature, ed_pub):
        # Create copies of the parameters to not modify the originals.
        signature = copy.deepcopy(signature)
        ed_pub    = copy.deepcopy(ed_pub)

        # Get the sign bit from the s part of the signature.
        sign_bit = (signature[63] >> 7) & 1

        # Set the sign bit to zero in the s part of the signature.
        signature[63] &= 0x7F

        # Restore the sign bit on the verification key, which should have 0 as its current
        # sign bit.
        ed_pub[31] |= sign_bit << 7

        # Here we use the fact, that
        # "XEd25519 signatures are valid Ed25519 signatures [1] and vice versa, [...]."
        # (https://signal.org/docs/specifications/xeddsa/#curve25519)
        # to reduce the amount of security critical code we have to write ourselves.

        data      = bytes(data)
        signature = bytes(signature)
        ed_pub    = bytes(ed_pub)

        try:
            return Ed25519VerificationKey(ed_pub).verify(data, signature) == data
        except BadSignatureError:
            return False
