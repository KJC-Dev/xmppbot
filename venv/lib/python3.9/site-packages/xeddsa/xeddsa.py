from __future__ import absolute_import

import os

class XEdDSA(object):
    """
    The base class for all XEdDSA implementations.
    Do not use this class directly, use subclasses for specific key types instead.

    The xeddsa.implementations module ships such subclasses.
    """

    MONT_PRIV_KEY_SIZE = NotImplemented
    MONT_PUB_KEY_SIZE  = NotImplemented
    ED_PRIV_KEY_SIZE   = NotImplemented
    ED_PUB_KEY_SIZE    = NotImplemented
    SIGNATURE_SIZE     = NotImplemented

    def __init__(self, mont_priv = None, mont_pub = None):
        """
        Create an XEdDSA object from Montgomery key material, to encrypt AND sign data
        using just one Montgomery key pair.

        :param mont_priv: A bytes-like object encoding the private key with length
            MONT_PRIV_KEY_SIZE or None.
        :param mont_pub: A bytes-like object encoding the public key with length
            MONT_PUB_KEY_SIZE or None.

        If both mont_priv and mont_pub are None, a new key pair is generated.
        """

        cls = self.__class__

        if not (
            isinstance(cls.MONT_PRIV_KEY_SIZE, int) and
            isinstance(cls.MONT_PUB_KEY_SIZE,  int) and
            isinstance(cls.ED_PRIV_KEY_SIZE,   int) and
            isinstance(cls.ED_PUB_KEY_SIZE,    int) and
            isinstance(cls.SIGNATURE_SIZE,     int)
        ):
            raise NotImplementedError("Can't instantiate the XEdDSA class directly.")

        if mont_priv == None and mont_pub == None:
            mont_priv = cls.generate_mont_priv()

        if not (mont_priv == None or isinstance(mont_priv, bytes)):
            raise TypeError("Wrong type passed for the mont_priv parameter.")

        if mont_priv != None and len(mont_priv) != cls.MONT_PRIV_KEY_SIZE:
            raise ValueError("Invalid value passed for the mont_priv parameter.")

        if mont_priv != None and mont_pub == None:
            mont_pub = cls.mont_pub_from_mont_priv(mont_priv)

        if not (mont_pub == None or isinstance(mont_pub, bytes)):
            raise TypeError("Wrong type passed for the mont_pub parameter.")

        if mont_pub != None and len(mont_pub) != cls.MONT_PUB_KEY_SIZE:
            raise ValueError("Invalid value passed for the mont_pub parameter.")

        self.__mont_priv = mont_priv
        self.__mont_pub  = mont_pub

    @classmethod
    def generate_mont_priv(cls):
        """
        Return a Montgomery private key to be used with XEdDSA.

        :returns: The private key as a bytes-like object with length MONT_PRIV_KEY_SIZE.
        """

        return bytes(cls._generate_mont_priv())

    @staticmethod
    def _generate_mont_priv():
        """
        Return a Montgomery private key to be used with XEdDSA.

        :returns: The private key as a bytearray with length MONT_PRIV_KEY_SIZE.
        """

        raise NotImplementedError

    @classmethod
    def mont_pub_from_mont_priv(cls, mont_priv):
        """
        Restore the Montgomery public key from a Montgomery private key.

        :param mont_priv: A bytes-like object encoding the private key with length
            MONT_PRIV_KEY_SIZE.
        :returns: A bytes-like object encoding the public key with length
            MONT_PUB_KEY_SIZE.
        """

        if not isinstance(mont_priv, bytes):
            raise TypeError("Wrong type passed for the mont_priv parameter.")

        if len(mont_priv) != cls.MONT_PRIV_KEY_SIZE:
            raise ValueError("Invalid value passed for the mont_priv parameter.")

        return bytes(cls._mont_pub_from_mont_priv(bytearray(mont_priv)))

    @staticmethod
    def _mont_pub_from_mont_priv(mont_priv):
        """
        Restore the Montgomery public key from a Montgomery private key.

        :param mont_priv: A bytearray encoding the private keywith length
            MONT_PRIV_KEY_SIZE.
        :returns: A bytearray encoding the public key with length MONT_PUB_KEY_SIZE.
        """

        raise NotImplementedError

    @classmethod
    def mont_priv_to_ed_pair(cls, mont_priv):
        """
        Derive a Twisted Edwards key pair from given Montgomery private key.

        :param mont_priv: A bytes-like object encoding the private key with length
            MONT_PRIV_KEY_SIZE.
        :returns: A tuple of bytes-like objects encoding the private key with length
            ED_PRIV_KEY_SIZE and the public key with length ED_PUB_KEY_SIZE.
        """

        if not isinstance(mont_priv, bytes):
            raise TypeError("Wrong type passed for the mont_priv parameter.")

        if len(mont_priv) != cls.MONT_PRIV_KEY_SIZE:
            raise ValueError("Invalid value passed for the mont_priv parameter.")

        ed_priv, ed_pub = cls._mont_priv_to_ed_pair(bytearray(mont_priv))

        return bytes(ed_priv), bytes(ed_pub)

    @staticmethod
    def _mont_priv_to_ed_pair(mont_priv):
        """
        Derive a Twisted Edwards key pair from given Montgomery private key.

        :param mont_priv: A bytearray encoding the private key with length
            MONT_PRIV_KEY_SIZE.
        :returns: A tuple of bytearrays encoding the private key with length
            ED_PRIV_KEY_SIZE and the public key with length ED_PUB_KEY_SIZE.
        """

        raise NotImplementedError

    @classmethod
    def mont_pub_to_ed_pub(cls, mont_pub):
        """
        Derive a Twisted Edwards public key from given Montgomery public key.

        :param mont_pub: A bytes-like object encoding the public key with length
            MONT_PUB_KEY_SIZE.
        :returns: A bytes-like object encoding the public key with length ED_PUB_KEY_SIZE.
        """

        if not isinstance(mont_pub, bytes):
            raise TypeError("Wrong type passed for the mont_pub parameter.")

        if len(mont_pub) != cls.MONT_PUB_KEY_SIZE:
            raise ValueError("Invalid value passed for the mont_pub parameter.")

        return bytes(cls._mont_pub_to_ed_pub(bytearray(mont_pub)))

    @staticmethod
    def _mont_pub_to_ed_pub(mont_pub):
        """
        Derive a Twisted Edwards public key from given Montgomery public key.

        :param mont_pub: A bytearray encoding the public key with length
            MONT_PUB_KEY_SIZE.
        :returns: A bytearray encoding the public key with length ED_PUB_KEY_SIZE.
        """

        raise NotImplementedError

    def sign(self, data, nonce = None):
        """
        Sign data using the Montgomery private key stored by this XEdDSA instance.

        :param data: A bytes-like object containing the data to sign.
        :param nonce: A bytes-like object with length 64 or None.
        :returns: A bytes-like object encoding the signature with length SIGNATURE_SIZE.

        If the nonce parameter is None, a new nonce is generated and used.

        :raises MissingKeyException: If the Montgomery private key is not available.
        """

        cls = self.__class__

        if not self.__mont_priv:
            raise MissingKeyException(
                "Cannot sign using this XEdDSA instance, Montgomery private key missing."
            )

        if not isinstance(data, bytes):
            raise TypeError("The data parameter must be a bytes-like object.")

        if nonce == None:
            nonce = os.urandom(64)

        if not isinstance(nonce, bytes):
            raise TypeError("Wrong type passed for the nonce parameter.")

        if len(nonce) != 64:
            raise ValueError("Invalid value passed for the nonce parameter.")

        ed_priv, ed_pub = cls._mont_priv_to_ed_pair(bytearray(self.__mont_priv))

        return bytes(cls._sign(
            bytearray(data),
            bytearray(nonce),
            ed_priv,
            ed_pub
        ))

    @staticmethod
    def _sign(data, nonce, ed_priv, ed_pub):
        """
        Sign data using given Twisted Edwards key pair.

        :param data: A bytearray containing the data to sign.
        :param nonce: A bytearray with length 64.
        :param ed_priv: A bytearray encoding the private key with length ED_PRIV_KEY_SIZE.
        :param ed_pub: A bytearray encoding the public key with length ED_PUB_KEY_SIZE.
        :returns: A bytearray encoding the signature with length SIGNATURE_SIZE.
        """

        raise NotImplementedError

    def verify(self, data, signature):
        """
        Verify signed data using the Montgomery public key stored by this XEdDSA instance.

        :param data: A bytes-like object containing the data that was signed.
        :param signature: A bytes-like object encoding the signature with length
            SIGNATURE_SIZE.
        :returns: A boolean indicating whether the signature was valid or not.
        """

        cls = self.__class__

        if not isinstance(data, bytes):
            raise TypeError("The data parameter must be a bytes-like object.")

        if not isinstance(signature, bytes):
            raise TypeError("Wrong type passed for the signature parameter.")

        if len(signature) != cls.SIGNATURE_SIZE:
            raise ValueError("Invalid value passed for the signature parameter.")

        return cls._verify(
            bytearray(data),
            bytearray(signature),
            cls._mont_pub_to_ed_pub(bytearray(self.__mont_pub))
        )

    @staticmethod
    def _verify(data, signature, ed_pub):
        """
        Verify signed data using given Twisted Edwards public key.

        :param data: A bytearray containing the data that was signed.
        :param signature: A bytearray encoding the signature with length SIGNATURE_SIZE.
        :returns: A boolean indicating whether the signature was valid or not.
        """

        raise NotImplementedError
