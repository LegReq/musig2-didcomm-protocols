from typing import List, Dict
import uuid
from buidl.taproot import MuSigTapScript, TapRootMultiSig, P2PKTapScript
from buidl.ecc import S256Point
from ..messages.cohort_set import CohortSetMessage
from ...sign.messages.request_signature import RequestSignatureMessage
# from ..message_types import COHORT_SET
from buidl.script import ScriptPubKey
from buidl.tx import TxOut, TxIn, Tx
import random


COHORT_ADVERTISED = "ADVERTISED"
COHORT_OPTED_IN = "OPTED_IN" 
COHORT_SET_STATUS = "COHORT_SET"
COHORT_FAILED = "FAILED"

COHORT_STATUS = [
    COHORT_ADVERTISED,
    COHORT_OPTED_IN,
    COHORT_SET_STATUS,
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
        self.cohort_keys: List[S256Point] = []
        self.min_participants = min_participants
        self.status = status
        self.btc_network = btc_network
        self.pending_signature_requests: Dict[str, str] = {}
        self.tr_merkle_root = None

    def add_participant(self, participant_did: str, participant_pk: str):
        """Add a participant to the cohort."""
        if participant_did not in self.participants:
            self.participants.append(participant_did)
            self.cohort_keys.append(participant_pk)

    def finalize_cohort(self):
        """Finalize the cohort and calculate the beacon address."""
        if len(self.participants) < self.min_participants:
            raise ValueError(f"Cohort {self.id} does not have enough participants to finalize.")
        self.status = COHORT_SET_STATUS
        self.beacon_address = self.calculate_beacon_address()

    def get_cohort_set_message(self, to, frm):
        """Get the cohort set message."""
        if self.status != COHORT_SET_STATUS:
            raise ValueError(f"Cohort {self.id} is not set.")
        return CohortSetMessage(
            to=to,
            frm=frm,
            cohort_id=self.id,
            thread_id=None,
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
        self.status = COHORT_SET_STATUS

    def calculate_beacon_address(self):
        """Calculate the beacon address for the cohort."""
        # musig = MuSigTapScript(self.cohort_keys)

        ## ADDITIONAL STEP BECAUSE OF BUG IN BUIDL LIBRARY
        ## p2tr musig2 must include a tweak
        tr_multisig = TapRootMultiSig(self.cohort_keys, len(self.cohort_keys))

        internal_pubkey = tr_multisig.default_internal_pubkey
        branch = tr_multisig.musig_tree()
        tr_merkle_root = branch.hash()
        self.tr_merkle_root = tr_merkle_root

        network = self.btc_network
        p2tr_beacon_address = internal_pubkey.p2tr_address(tr_merkle_root, network=network)

        return p2tr_beacon_address
    
    def get_cohort_musig2_script(self):
        """Get the MuSig2 script for the cohort."""
        musig = MuSigTapScript(self.cohort_keys)
        return musig
    
    def add_signature_request(self, request: RequestSignatureMessage):
        """Add a signature request to the cohort."""
        if not self.validate_signature_request(request):
            raise ValueError(f"Cohort {self.id} does not have the signature request {request.id}.")
        self.pending_signature_requests[request.frm] = request.data

      
    def validate_signature_request(self, request: RequestSignatureMessage):
        """Validate the signature request."""
        validated = True
        if request.cohort_id != self.id:
            print(f"Signature request for wrong cohort {request.cohort_id}.")
            validated = False
        if request.frm not in self.participants:
            print(f"Cohort {self.id} does not have the participant {request.frm}.")
            validated = False
        
        return validated
    
    def start_signing_session(self):
        """Start a signing session for the cohort."""
        print("DEBUG: Starting start_signing_session")
        from ...sign.models.signature_authorization import SignatureAuthorizationSession
        print(f"Starting signing session for cohort {self.id} with status {self.status}")
        if self.status != COHORT_SET_STATUS:   
            raise ValueError(f"Cohort {self.id} is not set.")
        
        print("DEBUG: Creating SMT root bytes")
        # TODO: need to construct the beacon signal from the pending signature requests
        # Construct the beacon signal with 32 random bytes
        smt_root_bytes = bytes([random.randint(0, 255) for _ in range(32)])

        print("DEBUG: Setting up transaction inputs")
        # TODO: Need to actually be spending a UTXO here
        funding_tx_id = "b33dabe7c6ccbbfe27487692d1c9318fe4c478d68347acc6e1714f5066f97f36"

        # TODO: Need to fund a beacon address
        prev_tx = bytes.fromhex(funding_tx_id)  # Identifying funding tx
        # prev_tx._value = 1000
        # prev_tx._script_pubkey = ScriptPubKey([0x6a, smt_root_bytes])
        prev_index = 1  # Identify funding output index

        tx_in = TxIn(prev_tx=prev_tx, prev_index=prev_index)

        

        print("DEBUG: Creating script pubkey")
        script_pubkey = ScriptPubKey([0x6a, smt_root_bytes])

        print("DEBUG: Creating beacon signal txout")
        beacon_signal_txout = TxOut(0, script_pubkey)

        tx_fee = 350
        
        print("DEBUG: Creating refund output")
        refund_amount = 500
        refund_out = TxOut.to_address(self.beacon_address, refund_amount)

        # tx_in._value = 1000
        # tx_in._script_pubkey = refund_out.script_pubkey

        tx_ins = [tx_in]

        tx_outs = [refund_out, beacon_signal_txout]

        print("DEBUG: Creating pending beacon signal")
        pending_beacon_signal = Tx(version=1, tx_ins=tx_ins, tx_outs=tx_outs, network=self.btc_network, segwit=True)

        print("DEBUG: Creating signing session")
        signing_session = SignatureAuthorizationSession(
            cohort=self,
            pending_tx=pending_beacon_signal,
            processed_requests=self.pending_signature_requests
        )

        print("DEBUG: Cleaning up and returning")
        self.pending_signature_requests = {}
        self.signing_session = signing_session
        print(f"Signing session {signing_session.id} created for cohort {self.id}")
        return signing_session