import uuid
from typing import List, Dict

from ..messages.authorization_request import AuthorizationRequestMessage
from buidl.ecc import S256Point
from ...keygen.models.cohort import Musig2Cohort
from buidl.tx import Tx, SIGHASH_DEFAULT


AWAITING_NONCE_CONTRIBUTIONS = "AWAITING_NONCE_CONTRIBUTIONS"
NONCE_CONTRIBUTION_SENT = "NONCE_CONTRIBUTION_SENT"
NONCE_CONTRIBUTIONS_RECEIVED = "NONCE_CONTRIBUTIONS_RECEIVED"
AWAITING_PARTIAL_SIGNATURES = "AWAITING_PARTIAL_SIGNATURES"
PARTIAL_SIGNATURES_RECEIVED = "PARTIAL_SIGNATURES_RECsEIVED"
SIGNATURE_COMPLETE = "SIGNATURE_COMPLETE"
FAILED = "FAILED"

class SignatureAuthorizationSession:   
    """Represents a MuSig2 signature authorization session"""

    def __init__(self, id: str = None, cohort: Musig2Cohort = None, pending_tx: Tx = None, processed_requests: Dict[str, str] = None, status: str = AWAITING_NONCE_CONTRIBUTIONS):
        self.id = id if id else str(uuid.uuid4())
        self.cohort = cohort
        self.pending_tx = pending_tx
        self.nonce_contributions = {}
        self.aggregated_nonce = None
        self.partial_signatures = {}
        self.signature = None
        self.status = status
        self.processed_requests: Dict[str, str] = processed_requests        
        self.nonce_secrets = None

    def get_authorization_request(self, frm: str, to: str):
        """Get the authorization request message for a participant."""
        tx_hex = self.pending_tx.serialize().hex()
        return AuthorizationRequestMessage(
            to=to,
            frm=frm,
            session_id=self.id,
            cohort_id=self.cohort.id,
            pending_tx=tx_hex
        )
    
    def set_nonce_secrets(self, nonce_secrets: list[S256Point]):
        """Set the participants nonce secrets for the session."""
        self.nonce_secrets = nonce_secrets
    
    def add_nonce_contribution(self, frm: str, nonce_contribution: list[str]):
        """Add a nonce contribution to the session."""
        if self.status != AWAITING_NONCE_CONTRIBUTIONS:
            raise ValueError(f"Nonce contributions already received. Current status: {self.status}")
        if len(nonce_contribution) != 2:
            raise ValueError(f"Invalid nonce contribution. Expected 2 points, got {len(nonce_contribution)}.")
        if self.nonce_contributions.get(frm):
            print(f"WARNING:Nonce contribution already received from {frm}.")

        self.nonce_contributions[frm] = nonce_contribution

        if len(self.nonce_contributions.items()) == len(self.cohort.participants):
            self.status = NONCE_CONTRIBUTIONS_RECEIVED

    def generate_aggregated_nonce(self):
        """Get the aggregated nonce for the session."""
        
        if self.status != NONCE_CONTRIBUTIONS_RECEIVED:
            raise ValueError(f"Nonce contributions not received yet. Received {len(self.nonce_contributions)} of {len(self.cohort.participants)}.")
        
        pub_nonces = []
        for frm, nonce_contribution in self.nonce_contributions.items():
            nonce_points = [S256Point.parse(bytes.fromhex(nonce)) for nonce in nonce_contribution]
            pub_nonces.append(nonce_points)

        musig = self.cohort.get_cohort_musig2_script()
        aggregated_nonce = musig.nonce_sums(pub_nonces)
        self.aggregated_nonce = aggregated_nonce
        
        return self.aggregated_nonce
    
    def set_aggregated_nonce(self, aggregated_nonce: list[S256Point]):
        """Set the aggregated nonce for the session."""
        self.aggregated_nonce = aggregated_nonce

    def generate_partial_signature(self, participant_sk):
        """Generate a partial signature for the session."""
        if self.aggregated_nonce is None:
            raise ValueError("Aggregated nonce not received yet.")
        
        input_index = 0
        
        sig_hash = self.pending_tx.sig_hash(0, SIGHASH_DEFAULT)
        musig = self.cohort.get_cohort_musig2_script()
        r = musig.compute_r(self.aggregated_nonce, sig_hash)
        k = musig.compute_k(self.nonce_secrets, self.aggregated_nonce, sig_hash)
        partial_sig = musig.sign(participant_sk, k, r, sig_hash, self.cohort.tr_merkle_root)
        return partial_sig
    
    def add_partial_signature(self, frm: str, partial_signature: int):
        """Add a partial signature to the session."""
        if self.status != AWAITING_PARTIAL_SIGNATURES:
            raise ValueError(f"Partial signatures not expected. Current status: {self.status}")
        if self.partial_signatures.get(frm):
            print(f"WARNING: Partial signature already received from {frm}.")
        self.partial_signatures[frm] = partial_signature
        if len(self.partial_signatures.items()) == len(self.cohort.participants):
            self.status = PARTIAL_SIGNATURES_RECEIVED

    def generate_final_signature(self):
        """Generate the final signature for the session."""
        if self.status != PARTIAL_SIGNATURES_RECEIVED:
            raise ValueError(f"Partial signatures not received yet. Current status: {self.status}")
        
        musig = self.cohort.get_cohort_musig2_script()
        input_index = len(self.pending_tx.tx_ins) - 1
        sig_hash = self.pending_tx.sig_hash(input_index, SIGHASH_DEFAULT)
        r = musig.compute_r(self.aggregated_nonce, sig_hash)
        sig_sum = 0
        for partial_sig in self.partial_signatures.values():
            print(f"Partial signature: {partial_sig}")
            print(f"Partial signature type: {type(partial_sig)}")
            sig_sum += partial_sig

        self.signature = musig.get_signature(sig_sum, r, sig_hash, self.cohort.tr_merkle_root)
        print(f"Signature: {self.signature.serialize().hex()}")
        
        tx_in_to_finalize = self.pending_tx.tx_ins[input_index]
        tx_in_to_finalize.finalize_p2tr_keypath(self.signature.serialize())
        tx_in_to_finalize._value = 1000
        tx_in_to_finalize._script_pubkey = self.pending_tx.tx_outs[0].script_pubkey
        print(f"Witness items: {len(tx_in_to_finalize.witness)}")
        for item in tx_in_to_finalize.witness:
            print(f"Witness item: {item.hex()} (length: {len(item)})")
    
        verified = self.pending_tx.verify()
        print(f"Verified: {verified}")
        print(f"btc network: {self.cohort.btc_network}")
        if not verified:
            raise ValueError("Signature verification failed.")
        self.status = SIGNATURE_COMPLETE
        print(f"Signature complete for session {self.id}")
        print(f"Signature: {self.signature.serialize().hex()}")
        self.signature = self.signature
        return self.signature

    def get_signature(self):
        """Get the signature for the session."""
        return self.signature
    