from ...messaging.base import BaseMessage
from ..message_types import COHORT_ADVERT

class CohortAdvertMessage(BaseMessage):
    """Message for announcing a new cohort."""


    def __init__(self, to: str, frm: str, thread_id: str, btc_network: str = "mainnet"):
        """Initialize a new cohort message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID
            thread_id: The cohort's ID
            btc_network: The Bitcoin network to use
        """
        super().__init__(COHORT_ADVERT, to, frm, thread_id) 
        self.btc_network = btc_network

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["btc_network"] = self.btc_network
        return msg_dict