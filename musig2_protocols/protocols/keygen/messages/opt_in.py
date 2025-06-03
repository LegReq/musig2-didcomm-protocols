from ....messaging.base import BaseMessage
from ..message_types import OPT_IN

class CohortOptInMessage(BaseMessage):
    """Message for joining a cohort."""


    def __init__(self, to: str, frm: str, thread_id: str, participant_pk: str):
        """Initialize a join cohort message.
        
        Args:
            to: The coordinator's DID
            frm: The participant's DID
            thread_id: The cohort's ID to join
            participant_pk: The participant's public key (hex encoded)
        """
        super().__init__(OPT_IN, to, frm, thread_id) 
        self.participant_pk = participant_pk

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
        msg_dict = super().to_dict()
        msg_dict["participant_pk"] = self.participant_pk
        return msg_dict