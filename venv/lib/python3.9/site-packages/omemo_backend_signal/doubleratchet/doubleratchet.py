from __future__ import absolute_import

import doubleratchet
import x3dh

from .cbcaead import CBCAEAD
from .rootchain import RootChain
from .symmetrickeyratchet import SymmetricKeyRatchet

class DoubleRatchet(doubleratchet.ratchets.DoubleRatchet):
    def __init__(
        self,
        ad,
        root_key,
        own_key   = None,
        other_pub = None
    ):
        super(DoubleRatchet, self).__init__(
            CBCAEAD(),                              # aead
            5000,                                   # message_key_store_max
            SymmetricKeyRatchet(),                  # symmetric_key_ratchet
            ad,                                     # ad
            x3dh.implementations.KeyPairCurve25519, # encryption_key_pair_class
            RootChain(root_key),                    # root_chain
            own_key,
            other_pub
        )

    def _makeAD(self, header, ad):
        return ad

    def encryptMessage(self, *args, **kwargs):
        result = super(DoubleRatchet, self).encryptMessage(*args, **kwargs)
        result["additional"] = result["ciphertext"]["additional"]
        result["ciphertext"] = result["ciphertext"]["ciphertext"]
        return result
