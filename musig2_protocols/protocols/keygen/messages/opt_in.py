from ....messaging.base import BaseMessage
from ..message_types import OPT_IN
from typing import Dict

class CohortOptInMessage(BaseMessage):
    """Message for joining a cohort."""


    def __init__(self, to: str, frm: str, cohort_id: str, participant_pk: str, thread_id: str = None):
        """Initialize a join cohort message.
        
        Args:
            to: The coordinator's DID
            frm: The participant's DID
            cohort_id: The cohort's ID to join
            thread_id: The thread id of the message (optional)
            participant_pk: The participant's public key (hex encoded)
        """
        body = {
            "cohort_id": cohort_id,
            "participant_pk": participant_pk
        }
        super().__init__(OPT_IN, to, frm, thread_id, body) 

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def participant_pk(self) -> str:
        return self.body["participant_pk"]
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != OPT_IN:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            participant_pk=msg_dict["body"]["participant_pk"],
            thread_id=msg_dict.get("thread_id")
        )