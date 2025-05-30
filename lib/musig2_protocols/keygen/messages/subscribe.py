from ...messaging.base import BaseMessage
from ..message_types import SUBSCRIBE

class SubscribeMessage(BaseMessage):
    """Message for subscribing to the MuSig2 coordinator."""


    def __init__(self, to: str, frm: str):
        """Initialize a subscribe message.
        
        Args:
            to: The coordinator's DID
            frm: The subscriber's DID
        """
        super().__init__(SUBSCRIBE, to, frm) 