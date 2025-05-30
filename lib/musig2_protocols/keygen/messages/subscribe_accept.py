from ...messaging.base import BaseMessage
from ..message_types import SUBSCRIBE_ACCEPT

class SubscribeAcceptMessage(BaseMessage):
    """Message for accepting a subscription request."""



    def __init__(self, to: str, frm: str):
        """Initialize a subscribe accept message.
        
        Args:
            to: The subscriber's DID
            frm: The coordinator's DID
        """
        super().__init__(SUBSCRIBE_ACCEPT, to, frm) 