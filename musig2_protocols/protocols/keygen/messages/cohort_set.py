from ....messaging.base import BaseMessage
from ..message_types import COHORT_SET

class CohortSetMessage(BaseMessage):
    """Message confirming the final cohort participants and beacon address."""

    def __init__(self, to: str, frm: str, thread_id: str, beacon_address: str, cohort_keys: list[str]):
        """Initialize a cohort set message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID 
            thread_id: The cohort's ID
            beacon_address: The n-of-n P2TR beacon address
            cohort_keys: List of hex-encoded public keys for all cohort participants
        """
        super().__init__(COHORT_SET, to, frm, thread_id)
        self.beacon_address = beacon_address
        self.cohort_keys = cohort_keys

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["beacon_address"] = self.beacon_address
        msg_dict["cohort_keys"] = self.cohort_keys
        return msg_dict
