from ....messaging.base import BaseMessage
from ..message_types import NONCE_CONTRIBUTION


class NonceContributionMessage(BaseMessage):
    """Message for contributing a nonce to the signature process."""

    def __init__(self, to: str, frm: str, session_id: str, cohort_id: str, nonce_contribution: list[str]):
        """Initialize a new nonce contribution message.
        
        Args:
            to: The recipient's DID
            frm: The sender's DID
            session_id: The session ID for musig2 signing session
            cohort_id: The ID of the cohort participating in the signing session
            nonce_contribution: An array of hex encoded S256k1 points that a participant is 
                                required to contribute as part of the nonce to the signature process.
        """
        super().__init__(NONCE_CONTRIBUTION, to, frm, session_id)
        self.cohort_id = cohort_id
        self.nonce_contribution = nonce_contribution

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["cohort_id"] = self.cohort_id
        msg_dict["nonce_contribution"] = self.nonce_contribution
        return msg_dict 
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["cohort_id"],
            session_id=msg_dict["thread_id"],
            nonce_contribution=msg_dict["nonce_contribution"]
        )