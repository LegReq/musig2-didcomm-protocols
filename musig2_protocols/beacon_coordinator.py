import uuid
from typing import List, Dict
from .didcomm_service import DIDCommService
from did_peer_2 import KeySpec, generate
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from aries_askar import Key, KeyAlg
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from .protocols.keygen.models.cohort import Musig2Cohort
from .protocols.keygen.messages.subscribe import SubscribeMessage
from .protocols.keygen.messages.subscribe_accept import SubscribeAcceptMessage
from .protocols.keygen.messages.cohort_advert import CohortAdvertMessage
from .protocols.keygen.messages.opt_in import CohortOptInMessage
from .protocols.keygen.message_types import SUBSCRIBE, OPT_IN
from .context import InMemoryContextStorage
from buidl.ecc import S256Point 
from .protocols.sign.messages.request_signature import RequestSignatureMessage
from .protocols.sign.message_types import REQUEST_SIGNATURE, NONCE_CONTRIBUTION, SIGNATURE_AUTHORIZATION
from .protocols.sign.models.signature_authorization import SignatureAuthorizationSession
from .protocols.sign.messages.nonce_contribution import NonceContributionMessage
from .protocols.sign.messages.aggregated_nonce import AggregatedNonceMessage
from .protocols.sign.messages.signature_authorization import SignatureAuthorizationMessage
from .protocols.sign.models.signature_authorization import AWAITING_PARTIAL_SIGNATURES, NONCE_CONTRIBUTIONS_RECEIVED, PARTIAL_SIGNATURES_RECEIVED

class BeaconCoordinator:
    """Coordinates MuSig2 protocol operations between participants."""

    async def __init__(self, name: str, host: str = "localhost", port: int = 8767):
        """Initialize the coordinator with DIDComm messaging service."""
        self.didcomm = DIDCommService(name, host, port)
        self.subscribers: List[str] = []
        self.cohorts: List[Musig2Cohort] = []
        self.active_signing_sessions: Dict[str, SignatureAuthorizationSession] = {}
        # TODO: Coodinator should be able to have many DIDs
        self.did = await self.didcomm.generate_did()

        # Register message handlers
        self.didcomm.register_message_handler(
            SUBSCRIBE,
            self._handle_subscribe
        )
        self.didcomm.register_message_handler(
            OPT_IN,
            self._handle_join_cohort
        )
        self.didcomm.register_message_handler(
            REQUEST_SIGNATURE,
            self._handle_request_signature
        )
        self.didcomm.register_message_handler(
            NONCE_CONTRIBUTION,
            self._handle_nonce_contribution
        )
        self.didcomm.register_message_handler(
            SIGNATURE_AUTHORIZATION,
            self._handle_signature_authorization
        )


    async def start(self):
        """Start the coordinator's DIDComm messaging service."""
        await self.didcomm.start_websocket_connection()

    async def _handle_subscribe(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle subscription requests from participants."""
        msg_sender = message["from"]
        if msg_sender not in self.subscribers:
            self.subscribers.append(msg_sender)

            await self.accept_subscription(msg_sender)

    async def _handle_join_cohort(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle join cohort requests from participants."""
        opt_in_msg = CohortOptInMessage.from_dict(message)
        cohort_id = opt_in_msg.cohort_id
        participant = opt_in_msg.frm
        participant_pk = opt_in_msg.participant_pk
        # Find the cohort
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        if cohort and participant not in cohort.participants:
            cohort.participants.append(participant)
            cohort.cohort_keys.append(S256Point.parse(bytes.fromhex(participant_pk)))
            
            # If we have enough participants, we can start the key generation
            if len(cohort.participants) >= cohort.min_participants:  # Minimum 2 participants
                await self._start_key_generation(cohort)

    async def _handle_request_signature(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle signature requests from participants."""
        signature_request = RequestSignatureMessage.from_dict(message)
        cohort = next((c for c in self.cohorts if c.id == signature_request.cohort_id), None)
        if cohort:
            cohort.add_signature_request(signature_request)
            print(f"Received signature request from {signature_request.frm} for cohort {signature_request.cohort_id}")
        else:
            print(f"Cohort {signature_request.cohort_id} not found.")

    async def _handle_nonce_contribution(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle nonce contributions from participants."""
        nonce_contribution_msg = NonceContributionMessage.from_dict(message)
        signing_session = self.active_signing_sessions.get(nonce_contribution_msg.cohort_id)
        if signing_session:
            if (signing_session.cohort.id != nonce_contribution_msg.cohort_id):
                raise ValueError(f"Nonce contribution for wrong cohort {nonce_contribution_msg.cohort_id}.")
            signing_session.add_nonce_contribution(nonce_contribution_msg.frm, nonce_contribution_msg.nonce_contribution)
            print(f"Received nonce contribution from {nonce_contribution_msg.frm} for session {nonce_contribution_msg.session_id}")

            if signing_session.status == NONCE_CONTRIBUTIONS_RECEIVED:
                await self.send_aggregated_nonce(signing_session)
        else:
            print(f"Session {nonce_contribution_msg.session_id} not found.")

    async def _handle_signature_authorization(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle signature authorization messages from participants."""
        signature_authorization_msg = SignatureAuthorizationMessage.from_dict(message)
        signing_session = self.active_signing_sessions.get(signature_authorization_msg.cohort_id)
        if signing_session:
            if signing_session.id != signature_authorization_msg.session_id:
                raise ValueError(f"Signature authorization message for wrong session {signature_authorization_msg.session_id}.")
            if signing_session.status != AWAITING_PARTIAL_SIGNATURES:
                raise ValueError(f"Partial signature received but not expected. Current status: {signing_session.status}")
            signing_session.add_partial_signature(signature_authorization_msg.frm, signature_authorization_msg.partial_signature)
            print(f"Received partial signature from {signature_authorization_msg.frm} for session {signature_authorization_msg.session_id}")
            if signing_session.status == PARTIAL_SIGNATURES_RECEIVED:
                signature = signing_session.generate_final_signature()
                print(f"Final signature: {signature.serialize().hex()}")

    async def accept_subscription(self, msg_sender: str):
        """Accept a subscription request from a participant."""
        print(f"Accepting subscription request from {msg_sender}")
        accept_msg = SubscribeAcceptMessage(
            to=msg_sender,
            frm=self.did
        )
        await self.didcomm.send_message(accept_msg.to_dict(), msg_sender, self.did)

    async def send_aggregated_nonce(self, signing_session):
        """Send the aggregated nonce to all participants in the signing session.
        
        Args:
            signing_session: The signing session containing the cohort and nonce information
        """
        aggregated_nonce = signing_session.generate_aggregated_nonce()
        signing_session.status = AWAITING_PARTIAL_SIGNATURES
        aggregated_nonces_hex = [point.sec().hex() for point in aggregated_nonce]
        
        for participant in signing_session.cohort.participants:
            msg = AggregatedNonceMessage(
                to=participant,
                frm=self.did,
                cohort_id=signing_session.cohort.id,
                session_id=signing_session.id,
                aggregated_nonce=aggregated_nonces_hex
            )
            await self.didcomm.send_message(
                msg.to_dict(),
                participant,
                self.did
            )
            print(f"Successfully sent aggregated nonce message to {participant}")

    async def announce_new_cohort(self, min_participants: int, btc_network: str = "signet"):
        """Announce a new cohort to all subscribers."""
        print(f"Creating new cohort and announcing to {len(self.subscribers)} subscribers")
        cohort = Musig2Cohort(min_participants=min_participants, btc_network=btc_network)
        self.cohorts.append(cohort)
        
        for subscriber in self.subscribers:
            print(f"Sending cohort announcement to {subscriber}")
            msg = CohortAdvertMessage(
                to=subscriber,
                frm=self.did,
                cohort_id=cohort.id,
                cohort_size=cohort.min_participants,
                thread_id=None,
                btc_network=btc_network
            )
            try:
                await self.didcomm.send_message(
                    msg.to_dict(),
                    subscriber,
                    self.did
                )
                print(f"Successfully sent cohort announcement {msg.type} to {subscriber}")
            except Exception as e:
                print(f"Error sending cohort announcement to {subscriber}: {str(e)}")
                # Remove failed subscriber
                self.subscribers.remove(subscriber)

        return cohort

    

    async def _start_key_generation(self, cohort: Musig2Cohort):
        """Start the key generation process for a cohort."""
        print(f"Starting key generation for cohort {cohort.id}")
        cohort.finalize_cohort()
        for participant in cohort.participants:
            msg = cohort.get_cohort_set_message(to=participant, frm=self.did)
            print(f"Sending COHORT_SET message to {participant}")
            await self.didcomm.send_message(
                msg.to_dict(),
                participant,
                self.did
            )
        print(f"Finished sending COHORT_SET message to {len(cohort.participants)} participants")


    """
    Start a signing session for a cohort.
    Sends authorization requests to all participants in the cohort.
    """
    async def start_signing_session(self, cohort_id: str):
        """Start a signing session for a cohort."""
        print(f"Attempting to start signing session for {cohort_id}")
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        if cohort:
            print(f"Cohort {cohort_id} found. Starting signing session.")
            signing_session = cohort.start_signing_session()
            print(f"Starting signing session {signing_session.id} for cohort {cohort_id}")
            for participant in cohort.participants:
                msg = signing_session.get_authorization_request(participant, self.did)
                print(f"Sending authorization request to {participant}")
                await self.didcomm.send_message(
                    msg.to_dict(),
                    participant,
                    self.did)
            self.active_signing_sessions[cohort_id] = signing_session
        else:
            print(f"Cohort {cohort_id} not found.")

    @classmethod
    async def create(cls, name: str, host: str = "localhost", port: int = 8767):
        """Create a new coordinator instance."""
        self = cls.__new__(cls)
        await self.__init__(name, host, port)
        return self 