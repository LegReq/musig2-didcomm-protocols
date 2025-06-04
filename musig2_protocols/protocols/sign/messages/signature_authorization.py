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
        body = {
            # TODO: Wondering again is session_id could just be the thread_id?
            # My sesnse is that a thread is between two interacting parties sending messages back and forth. 
            # Wheras the signing session is between the cohort participants and coordinator.
            "session_id": session_id,
            "cohort_id": cohort_id,
            "partial_signature": partial_signature
        }
        thread_id = None
        super().__init__(SIGNATURE_AUTHORIZATION, to, frm, thread_id, body)

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def partial_signature(self) -> int:
        return self.body["partial_signature"]
    
    @property
    def session_id(self) -> str:
        return self.body["session_id"]
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != SIGNATURE_AUTHORIZATION:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            session_id=msg_dict["body"]["session_id"],
            partial_signature=msg_dict["body"]["partial_signature"]
        )