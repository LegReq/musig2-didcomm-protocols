from typing import Dict, Optional
import uuid


class BaseMessage:
    """Base class for all MuSig2 protocol messages."""

    def __init__(
        self,
        msg_type: str,
        to: str,
        frm: str,
        thread_id: Optional[str] = None,
        body: Optional[Dict] = None
    ):
        """Initialize a base message.
        
        Args:
            msg_type: The type of message (e.g. "https://didcomm.org/musig2/subscribe")
            to: The recipient's DID
            frm: The sender's DID
            thread_id: Optional thread ID for message threading
            body: Optional message body
        """
        self.type = msg_type
        self.id = str(uuid.uuid4())
        self.to = to
        self.from_ = frm
        self.thread_id = thread_id
        self.body = body or {}

    def to_dict(self) -> Dict:
        """Convert the message to a dictionary."""
        msg_dict = {
            "type": self.type,
            "id": self.id,
            "to": self.to,
            "from": self.from_,
            "body": self.body
        }
        if self.thread_id:
            msg_dict["thread_id"] = self.thread_id
        return msg_dict 