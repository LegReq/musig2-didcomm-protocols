from ....messaging.base import BaseMessage
from ..message_types import COHORT_ADVERT
from typing import Dict

class CohortAdvertMessage(BaseMessage):
    """Message for announcing a new cohort."""


    def __init__(self, to: str, frm: str, cohort_id: str, cohort_size: int, beacon_type: str, thread_id: str = None, btc_network: str = "mainnet"):
        """Initialize a new cohort message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID
            thread_id: The thread id of the message (optional)
            cohort_id: The cohort's ID
            cohort_size: The size of the cohort
            btc_network: The Bitcoin network of the cohort
        """
        body = {
            "cohort_id": cohort_id,
            "btc_network": btc_network,
            "cohort_size": cohort_size,
            "beacon_type": beacon_type
        }
        
        super().__init__(COHORT_ADVERT, to, frm, thread_id, body) 

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]

    @property
    def cohort_size(self) -> int:
        return self.body["cohort_size"]
    
    @property
    def btc_network(self) -> str:
        return self.body["btc_network"]
    
    @property
    def beacon_type(self) -> str:
        return self.body["beacon_type"]
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != COHORT_ADVERT:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls( 
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            cohort_size=msg_dict["body"]["cohort_size"],
            thread_id=msg_dict.get("thread_id"),
            btc_network=msg_dict["body"]["btc_network"],
            beacon_type=msg_dict["body"]["beacon_type"]
        )