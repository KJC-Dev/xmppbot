from __future__ import absolute_import

import doubleratchet

from .sendrecvchain import SendRecvChain

class SymmetricKeyRatchet(doubleratchet.ratchets.SymmetricKeyRatchet):
    def __init__(self):
        super(SymmetricKeyRatchet, self).__init__(
            SendRecvChain,
            SendRecvChain
        )
