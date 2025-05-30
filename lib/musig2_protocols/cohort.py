from typing import List, Dict
import uuid
from buidl.taproot import MuSigTapScript, TapRootMultiSig, P2PKTapScript
from buidl.ecc import S256Point
from .keygen.messages.cohort_set import CohortSetMessage
COHORT_ADVERTISED = "ADVERTISED"
COHORT_OPTED_IN = "OPTED_IN" 
COHORT_SET = "COHORT_SET"
COHORT_FAILED = "FAILED"

COHORT_STATUS = [
    COHORT_ADVERTISED,
    COHORT_OPTED_IN,
    COHORT_SET,
    COHORT_FAILED
]

class Musig2Cohort:
    """Represents a MuSig2 cohort with its participants and keys."""
    
    def __init__(self, id: str = None, min_participants: int = 2, status: str = COHORT_ADVERTISED, btc_network: str = "mainnet", coordinator_did: str = None):
        self.id = id if id else str(uuid.uuid4())
        # Need to model participants as a channel DID, and a set of keys
        # May also want to model coordinator as a DID
        self.coordinator_did = coordinator_did
        self.participants: List[str] = []
        self.cohort_keys: List[str] = []
        self.min_participants = min_participants
        self.status = status
        self.btc_network = btc_network

    def add_participant(self, participant_did: str, participant_pk: str):
        """Add a participant to the cohort."""
        if participant_did not in self.participants:
            self.participants.append(participant_did)
            self.cohort_keys.append(participant_pk)

    def finalize_cohort(self):
        """Finalize the cohort and calculate the beacon address."""
        if len(self.participants) < self.min_participants:
            raise ValueError(f"Cohort {self.id} does not have enough participants to finalize.")
        self.status = COHORT_SET
        self.beacon_address = self.calculate_beacon_address()

    def get_cohort_set_message(self, to, frm):
        """Get the cohort set message."""
        if self.status != COHORT_SET:
            raise ValueError(f"Cohort {self.id} is not set.")
        return CohortSetMessage(
            to=to,
            frm=frm,
            thread_id=self.id,
            beacon_address=self.beacon_address,
            cohort_keys=[pk.sec().hex() for pk in self.cohort_keys]
        )

    def validate_cohort(self, participant_keys: List[str], cohort_keys: List[str], beacon_address: str):
        """Validate the cohort."""
        for participant_key in participant_keys:
            if participant_key not in cohort_keys:
                self.status = COHORT_FAILED
                raise ValueError(f"Cohort {self.id} does not have contain the participant key {participant_key}.")

        self.cohort_keys = [S256Point.parse(bytes.fromhex(hex_key)) for hex_key in cohort_keys]
        calculated_beacon_address = self.calculate_beacon_address()
        if calculated_beacon_address != beacon_address:
            self.status = COHORT_FAILED
            raise ValueError(f"Cohort {self.id} beacon address does not match.")
        self.beacon_address = calculated_beacon_address
        self.status = COHORT_SET

    def calculate_beacon_address(self):
        """Calculate the beacon address for the cohort."""
        # musig = MuSigTapScript(self.cohort_keys)

        ## ADDITIONAL STEP BECAUSE OF BUG IN BUIDL LIBRARY
        ## p2tr musig2 must include a tweak
        tr_multisig = TapRootMultiSig(self.cohort_keys, len(self.cohort_keys))

        internal_pubkey = tr_multisig.default_internal_pubkey
        branch = tr_multisig.musig_tree()
        tr_merkle_root = branch.hash()

        network = self.btc_network
        p2tr_beacon_address = internal_pubkey.p2tr_address(tr_merkle_root, network=network)

        return p2tr_beacon_address