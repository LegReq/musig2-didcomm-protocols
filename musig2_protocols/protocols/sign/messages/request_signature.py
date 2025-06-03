from ....messaging.base import BaseMessage
from ..message_types import REQUEST_SIGNATURE
from typing import Dict
import uuid

class RequestSignatureMessage(BaseMessage):
    """Message for requesting a signature from participants."""

    def __init__(self, to: str, frm: str, thread_id: str, cohort_id: str, data: str):
        """Initialize a new request signature message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID
            thread_id: The thread ID for this signature request
            cohort_id: The ID of the cohort participating in the signing session
            data: Additional data that can be used to customise the signature request. This is where we can send the btc1 payload hash.
        """
        thread_id = thread_id if thread_id else str(uuid.uuid4())
        super().__init__(REQUEST_SIGNATURE, to, frm, thread_id)
        self.cohort_id = cohort_id
        self.data = data

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["cohort_id"] = self.cohort_id
        msg_dict["data"] = self.data
        return msg_dict 
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["cohort_id"],
            thread_id=msg_dict["thread_id"],
            data=msg_dict["data"]
        )