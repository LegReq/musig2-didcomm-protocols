from ....messaging.base import BaseMessage
from ..message_types import AUTHORIZATION_REQUEST
from typing import Dict

class AuthorizationRequestMessage(BaseMessage):
    """Message for requesting authorization from cohort participants to sign a bitcoin transaction."""

    def __init__(self, to: str, frm: str, session_id: str, cohort_id: str, pending_tx: str):
        """Initialize a new authorization request message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID
            session_id: The session ID for this musig2 signing session
            cohort_id: The ID of the cohort participating in the signing session
            pending_tx: The pending bitcoin transaction (hex encoded) to be signed
        """
        body = {
            "session_id": session_id,
            "cohort_id": cohort_id,
            "pending_tx": pending_tx
        }
        thread_id = None
        super().__init__(AUTHORIZATION_REQUEST, to, frm, thread_id, body)

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def pending_tx(self) -> str:
        return self.body["pending_tx"]
    
    @property
    def session_id(self) -> str:
        return self.body["session_id"]
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != AUTHORIZATION_REQUEST:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            session_id=msg_dict["body"]["session_id"],
            pending_tx=msg_dict["body"]["pending_tx"]
        )