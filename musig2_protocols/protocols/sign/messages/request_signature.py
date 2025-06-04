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
        body = {
            "cohort_id": cohort_id,
            # TODO: Review use of data field. This is to make the protocol messages generic, rather than btc1 specific. 
            # Is this a good idea?
            "data": data
        }
        super().__init__(REQUEST_SIGNATURE, to, frm, thread_id, body)

    @property
    def data(self) -> str:
        return self.body["data"]
    
    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def session_id(self) -> str:
        return self.body["session_id"]
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != REQUEST_SIGNATURE:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            thread_id=msg_dict.get("thread_id"),
            data=msg_dict["body"]["data"]
        )