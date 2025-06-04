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
        body = {
            "session_id": session_id,
            "cohort_id": cohort_id,
            "nonce_contribution": nonce_contribution
        }
        thread_id = None
        super().__init__(NONCE_CONTRIBUTION, to, frm, thread_id, body)

    @property
    def session_id(self) -> str:
        return self.body["session_id"]
    
    @property
    def cohort_id(self) -> str:
        return self.body["cohort_id"]
    
    @property
    def nonce_contribution(self) -> list[str]:
        return self.body["nonce_contribution"]
    
    @classmethod
    def from_dict(cls, msg_dict: dict):
        """Create a message instance from a dictionary."""
        if msg_dict["type"] != NONCE_CONTRIBUTION:
            raise ValueError(f"Invalid message type: {msg_dict['type']}")
        return cls(
            to=msg_dict["to"],
            frm=msg_dict["from"],
            cohort_id=msg_dict["body"]["cohort_id"],
            session_id=msg_dict["body"]["session_id"],
            nonce_contribution=msg_dict["body"]["nonce_contribution"]
        )