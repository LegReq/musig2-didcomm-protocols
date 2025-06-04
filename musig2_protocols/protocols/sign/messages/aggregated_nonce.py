from ....messaging.base import BaseMessage
from ..message_types import AGGREGATED_NONCE


class AggregatedNonceMessage(BaseMessage):
    """Message containing the aggregated nonce for all participants."""

    def __init__(self, to: str, frm: str, cohort_id: str, session_id: str, aggregated_nonce: list[str]):
        """Initialize a new aggregated nonce message.
        
        Args:
            to: The recipient's DID
            frm: The coordinator's DID
            cohort_id: The cohort ID for this musig2 signing session
            session_id: The session ID for this musig2 signing session
            aggregated_nonce: The combined musig2 nonce values from all participants in the signing session.
        """
        body = {
            "session_id": session_id,
            "cohort_id": cohort_id,
            "session_id": session_id,
            "aggregated_nonce": aggregated_nonce
        }
        thread_id = None
        super().__init__(AGGREGATED_NONCE, to, frm, thread_id, body)

    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def session_id(self) -> str:
        return self.body["session_id"]
    
    @property
    def aggregated_nonce(self) -> list[str]:
        return self.body["aggregated_nonce"]
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != AGGREGATED_NONCE:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            session_id=msg_dict["body"]["session_id"],
            aggregated_nonce=msg_dict["body"]["aggregated_nonce"]
        )