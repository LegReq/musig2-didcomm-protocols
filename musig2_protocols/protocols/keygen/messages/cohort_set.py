from ....messaging.base import BaseMessage
from ..message_types import COHORT_SET
from typing import Dict

class CohortSetMessage(BaseMessage):
    """Message confirming the final cohort participants and beacon address."""

    def __init__(self, to: str, frm: str, thread_id: str, cohort_id: str, beacon_address: str, cohort_keys: list[str]):
        """Initialize a cohort set message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID 
            thread_id: The thread id of the message
            cohort_id: The cohort's ID
            beacon_address: The n-of-n P2TR beacon address
            cohort_keys: List of hex-encoded public keys for all cohort participants
        """
        body = {
            "cohort_id": cohort_id,
            "beacon_address": beacon_address,
            "cohort_keys": cohort_keys
        }
        super().__init__(COHORT_SET, to, frm, thread_id, body)

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def beacon_address(self) -> str:
        return self.body["beacon_address"]
    
    @property
    def cohort_keys(self) -> list[str]:
        return self.body["cohort_keys"]

    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != COHORT_SET:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            thread_id=msg_dict.get("thread_id"),
            cohort_id=msg_dict["body"]["cohort_id"],
            beacon_address=msg_dict["body"]["beacon_address"],
            cohort_keys=msg_dict["body"]["cohort_keys"]
        )