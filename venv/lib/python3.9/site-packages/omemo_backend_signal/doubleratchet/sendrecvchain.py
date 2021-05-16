from __future__ import absolute_import

import doubleratchet

class SendRecvChain(doubleratchet.kdfchains.ConstKDFChain):
    def __init__(self, key):
        super(SendRecvChain, self).__init__(
            None,
            doubleratchet.recommended.ChainKeyKDF("SHA-256"),
            key
        )
