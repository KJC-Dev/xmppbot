from __future__ import absolute_import

from .x3dhpkencoder import X3DHPKEncoder

import x3dh

class State(x3dh.State):
    def __init__(self):
        """
        Sets the constructor parameters to the defaults used by OMEMO.
        The curve, min_num_otpks and max_num_otpks parameters were found in the XEP
        (https://xmpp.org/extensions/xep-0384.html).

        The hash_function and info_string parameters were found in the source code of
        libsignal-protocol-java
        (https://github.com/WhisperSystems/libsignal-protocol-java).

        The timeout for the SPK is defaulted to one week.
        """

        return super(State, self).__init__(
            "WhisperText".encode("US-ASCII"), # info_string
            "25519",                          # curve
            "SHA-256",                        # hash_function
            7 * 24 * 60 * 60,                 # spk_timeout
            20,                               # min_num_otpks
            100,                              # max_num_otpks
            X3DHPKEncoder                     # public_key_encoder_class
        )

    def getSharedSecretActive(self, *args, **kwargs):
        # X3DH is specified to build the associated data as follows: IK_A || IK_B.
        # As per usual, WhisperSystems weren't satisfied with their own solution and
        # instead of using the ad as built by X3DH they ALWAYS do:
        #     IK_sender || IK_receiver.
        # That means, when decrypting a message, a different ad is used as when encrypting
        # a message.
        #
        # To allow for this to happen, the ad is reordered so that it always has following
        # structure: IK_own || IK_other.

        result = super(State, self).getSharedSecretActive(*args, **kwargs)

        IK_own   = result["ad"][:33]
        IK_other = result["ad"][33:]

        result["ad"] = IK_own + IK_other

        return result

    def getSharedSecretPassive(self, *args, **kwargs):
        result = super(State, self).getSharedSecretPassive(*args, **kwargs)

        # See getSharedSecretActive for an explanation
        IK_own   = result["ad"][33:]
        IK_other = result["ad"][:33]

        result["ad"] = IK_own + IK_other

        return result
