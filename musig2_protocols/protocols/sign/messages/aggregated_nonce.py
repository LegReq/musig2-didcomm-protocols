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
        super().__init__(AGGREGATED_NONCE, to, frm, session_id)
        self.aggregated_nonce = aggregated_nonce
        self.cohort_id = cohort_id

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["cohort_id"] = self.cohort_id
        msg_dict["aggregated_nonce"] = self.aggregated_nonce
        return msg_dict 
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["cohort_id"],
            session_id=msg_dict["thread_id"],
            aggregated_nonce=msg_dict["aggregated_nonce"]
        )