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
        super().__init__(AUTHORIZATION_REQUEST, to, frm, session_id)
        self.cohort_id = cohort_id
        self.pending_tx = pending_tx

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["cohort_id"] = self.cohort_id
        msg_dict["pending_tx"] = self.pending_tx
        return msg_dict 
    
    @classmethod
    def from_dict(cls, msg_dict: Dict):
        """Create a message instance from a dictionary."""
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["cohort_id"],
            session_id=msg_dict["thread_id"],
            pending_tx=msg_dict["pending_tx"]
        )