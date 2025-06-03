from ....messaging.base import BaseMessage
from ..message_types import SIGNATURE_AUTHORIZATION


class SignatureAuthorizationMessage(BaseMessage):
    """Message for authorizing a signature contribution."""

    def __init__(self, to: str, frm: str, cohort_id: str, session_id: str, partial_signature: int):
        """Initialize a new signature authorization message.
        
        Args:
            to: The recipient's DID
            frm: The sender's DID
            cohort_id: The cohort ID for this musig2 signing session
            session_id: The session ID for this musig2 signing session
            partial_signature: A participants partial signature contribution to the signature.
        """
        super().__init__(SIGNATURE_AUTHORIZATION, to, frm, session_id)
        self.cohort_id = cohort_id
        self.partial_signature = partial_signature

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["cohort_id"] = self.cohort_id
        msg_dict["partial_signature"] = self.partial_signature
        return msg_dict 
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["cohort_id"],
            session_id=msg_dict["thread_id"],
            partial_signature=msg_dict["partial_signature"]
        )