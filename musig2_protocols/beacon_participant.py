from typing import List, Dict
from .didcomm_service import DIDCommService
from did_peer_2 import KeySpec, generate
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from aries_askar import Key, KeyAlg
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from .protocols.keygen.messages.subscribe import SubscribeMessage
from .protocols.keygen.messages.subscribe_accept import SubscribeAcceptMessage
from .protocols.keygen.messages.cohort_advert import CohortAdvertMessage
from .protocols.keygen.messages.opt_in import CohortOptInMessage
from .protocols.keygen.models.cohort import Musig2Cohort
from .protocols.keygen.message_types import SUBSCRIBE_ACCEPT, COHORT_ADVERT, COHORT_SET
from .context import InMemoryContextStorage
from buidl.hd import HDPrivateKey
from .protocols.sign.message_types import AUTHORIZATION_REQUEST, AGGREGATED_NONCE
from .protocols.keygen.models.cohort import COHORT_OPTED_IN, COHORT_SET_STATUS
from .protocols.sign.messages.request_signature import RequestSignatureMessage
from .protocols.sign.messages.authorization_request import AuthorizationRequestMessage
from .protocols.sign.models.signature_authorization import SignatureAuthorizationSession
from .protocols.sign.messages.nonce_contribution import NonceContributionMessage
from .protocols.sign.messages.aggregated_nonce import AggregatedNonceMessage
from .protocols.sign.messages.signature_authorization import SignatureAuthorizationMessage
from .protocols.keygen.messages.cohort_set import CohortSetMessage
from buidl.ecc import S256Point
from buidl.tx import Tx

# Future: Might have multiple keys per cohort
class CohortKeyState:
    """Tracks a participant's key state within a cohort."""
    
    def __init__(self, cohort_id: str, own_did: str, key_index: int):
        self.cohort_id = cohort_id
        self.key_index = key_index  # HD wallet key index
        self.own_did = own_did


class BeaconParticipant:
    """Represents a participant in the MuSig2 protocol that can join cohorts."""

    async def __init__(self, root_hdpriv: HDPrivateKey, name: str, host: str = "localhost", port: int = 8766):
        """Initialize the participant with DIDComm messaging service."""
        self.didcomm = DIDCommService(name, host, port)
        self.root_hdpriv = root_hdpriv
        self.next_beacon_key_index = 0
        self.coordinator_dids: List[str] = []
        self.cohorts: List[Musig2Cohort] = []
        self.cohort_key_state:  Dict[str, CohortKeyState] = {}
        self.did = await self.didcomm.generate_did()
        self.active_signing_sessions: Dict[str, SignatureAuthorizationSession] = {}

        # Register message handlers
        self.didcomm.register_message_handler(
            SUBSCRIBE_ACCEPT,
            self._handle_subscribe_accept
        )
        self.didcomm.register_message_handler(
            COHORT_ADVERT,
            self._handle_cohort_advert
        )
        self.didcomm.register_message_handler(
            COHORT_SET,
            self._handle_cohort_set
        )

        self.didcomm.register_message_handler(
            AUTHORIZATION_REQUEST,
            self._handle_authorization_request
        )
        self.didcomm.register_message_handler(
            AGGREGATED_NONCE,
            self._handle_aggregated_nonce
        )

    # TODO: This is a bit of a hack. We should be using a HD wallet to manage the keys.
    # TODO: refactor this so that it takes a cohort_id and returns the key for that cohort.
    def get_cohort_key(self, index: int = None):
        """Get the beacon key for a given index."""
        if index is None:
            index = self.next_beacon_key_index
            self.next_beacon_key_index += 1
        return self.root_hdpriv.get_private_key(index)

    async def start(self):
        """Start the participant's DIDComm messaging service."""
        await self.didcomm.start_websocket_connection()

    async def subscribe_to_coordinator(self, coordinator_did: str):
        """Subscribe to a coordinator to receive cohort announcements."""
        if coordinator_did not in self.coordinator_dids:
            msg = SubscribeMessage(
                to=coordinator_did,
                frm=self.did
            )
            await self.didcomm.send_message(
                msg.to_dict(),
                coordinator_did,
                self.did
            )

    async def _handle_subscribe_accept(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle subscription acceptance from a coordinator."""
        coordinator_did = message["from"]   
        if coordinator_did not in self.coordinator_dids:
            self.coordinator_dids.append(coordinator_did)

    async def _handle_cohort_advert(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        print(f"BeaconParticipant {self.did} received new cohort announcement from {message['from']}")
        """Handle new cohort announcements from coordinators."""
        cohort_advert = CohortAdvertMessage.from_dict(message)
        cohort_id = cohort_advert.cohort_id
        btc_network = cohort_advert.btc_network
        frm = cohort_advert.frm
        if frm not in self.coordinator_dids:
            print(f"BeaconParticipant {self.did} received unsolicited new cohort announcement from {frm}")
            return
        
        cohort = Musig2Cohort(id=cohort_id, btc_network=btc_network, coordinator_did=frm)
        self.cohorts.append(cohort)
        # May configure additional rules or await user input to join the cohort
        # Automatically join the new cohort
        await self.join_cohort(cohort.id, message["from"])

    async def _handle_cohort_set(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle cohort set messages from coordinators."""
        cohort_set_msg = CohortSetMessage.from_dict(message)
        cohort_id = cohort_set_msg.cohort_id
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        cohort_key_state = self.cohort_key_state[cohort_id]
        participant_pk = self.get_cohort_key(cohort_key_state.key_index).point.sec().hex()
        beacon_address = cohort_set_msg.beacon_address
        cohort_keys = cohort_set_msg.cohort_keys
        cohort.validate_cohort([participant_pk], cohort_keys, beacon_address)
        print(f"BeaconParticipant {self.didcomm.name} validated cohort {cohort_id} with beacon address {beacon_address}. Cohort status: {cohort.status}")

    async def _handle_authorization_request(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle authorization requests from coordinators."""
        authorization_request = AuthorizationRequestMessage.from_dict(message)
        cohort = next((c for c in self.cohorts if c.id == authorization_request.cohort_id), None)
        if cohort:
            signing_session = SignatureAuthorizationSession(
                cohort=cohort,
                id=authorization_request.session_id,
                pending_tx=Tx.parse_hex(authorization_request.pending_tx, network=cohort.btc_network)
            )   
            # TODO: Validate the signing_session against a pending request
            self.active_signing_sessions[cohort.id] = signing_session

            nonce_contribution = self.generate_nonce_contribution(cohort, signing_session)
            print(nonce_contribution)
            await self.send_nonce_contribution(cohort, nonce_contribution, signing_session)

        else:
            print(f"Cohort {authorization_request.cohort_id} not found.")

    async def _handle_aggregated_nonce(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle aggregated nonce messages from coordinators."""
        aggregated_nonce_msg = AggregatedNonceMessage.from_dict(message)
        signing_session = self.active_signing_sessions.get(aggregated_nonce_msg.cohort_id)
        
        if signing_session:
            if signing_session.id != aggregated_nonce_msg.session_id:
                print(f"Aggregated nonce message for wrong session {aggregated_nonce_msg.session_id}.")
                return
            
            aggregated_nonce = [S256Point.parse(bytes.fromhex(nonce)) for nonce in aggregated_nonce_msg.aggregated_nonce]
            signing_session.set_aggregated_nonce(aggregated_nonce)

            cohort_key_state = self.cohort_key_state.get(signing_session.cohort.id)
            if not cohort_key_state:
                print(f"Cohort key state not found for cohort {signing_session.cohort.id}")
                return
            
            participant_sk = self.get_cohort_key(cohort_key_state.key_index)
            partial_sig = signing_session.generate_partial_signature(participant_sk)
            await self.send_partial_signature(signing_session, partial_sig)

            print(f"Received aggregated nonce from {aggregated_nonce_msg.frm} for session {aggregated_nonce_msg.session_id}")


    async def join_cohort(self, cohort_id: str, coordinator_did: str):
        """Join a specific cohort."""
        print(f"BeaconParticipant {self.did} joining cohort {cohort_id} with coordinator {coordinator_did}")
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)

        if cohort is not None:
            key_index = self.next_beacon_key_index
            participant_pk = self.get_cohort_key().point.sec().hex()
            cohort_key_state = CohortKeyState(cohort_id, self.did, key_index)
            self.cohort_key_state[cohort_id] = cohort_key_state

            msg = CohortOptInMessage(
                to=coordinator_did,
                frm=self.did,
                cohort_id=cohort_id,
                # TODO: Should I be using thread_id here? Could thread_id be the cohort_id?
                thread_id=None,
                participant_pk=participant_pk
            )
            await self.didcomm.send_message(
                msg.to_dict(),
                coordinator_did,
                self.did
            )
            cohort.status = COHORT_OPTED_IN

    async def request_cohort_signature(self, cohort_id: str, data: str):
        """Request a signature for a cohort."""
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        if cohort:
            if cohort.status != COHORT_SET_STATUS:
                print(f"Cohort {cohort_id} not in set state.")
                print(cohort.status == COHORT_SET_STATUS)
                return False
            
            # TODO: Need to save the signing request somewhere
            msg = RequestSignatureMessage(
                to=cohort.coordinator_did,
                frm=self.did,
                thread_id=None,
                cohort_id=cohort_id,
                data=data
            )
            await self.didcomm.send_message(
                msg.to_dict(),
                cohort.coordinator_did,
                self.did
            )
            return True
        else:
            print(f"Cohort {cohort_id} not found.")
            return False

    def generate_nonce_contribution(self, cohort: Musig2Cohort, signing_session: SignatureAuthorizationSession):
        """Generate a nonce contribution for a signing session."""

        cohort_key_state = self.cohort_key_state.get(cohort.id)
        if cohort_key_state:
            musig_script = cohort.get_cohort_musig2_script()
            nonce_secrets, nonce_points = musig_script.generate_nonces();
            signing_session.set_nonce_secrets(nonce_secrets)
            nonce_contribution = [point.sec().hex() for point in nonce_points]
            return nonce_contribution
        else:
            print(f"Key for cohort {cohort.id} not found.")

    async def send_nonce_contribution(self, cohort: Musig2Cohort, nonce_contribution: list[str], signing_session: SignatureAuthorizationSession):
        """Send a nonce contribution to the coordinator."""
        msg = NonceContributionMessage(
            to=cohort.coordinator_did,
            frm=self.did,
            session_id=signing_session.id,
            cohort_id=cohort.id,
            nonce_contribution=nonce_contribution
        )
        await self.didcomm.send_message(
            msg.to_dict(),
            cohort.coordinator_did,
            self.did
        )

    async def send_partial_signature(self, signing_session: SignatureAuthorizationSession, partial_signature: str):
        """Send a partial signature to the coordinator."""
        msg = SignatureAuthorizationMessage(
            to=signing_session.cohort.coordinator_did,
            frm=self.did,
            cohort_id=signing_session.cohort.id,
            session_id=signing_session.id,
            partial_signature=partial_signature
        )
        await self.didcomm.send_message(
            msg.to_dict(),
            signing_session.cohort.coordinator_did,
            self.did
        )

    @classmethod
    async def create(cls, root_hdpriv: HDPrivateKey, name: str, host: str = "localhost", port: int = 8766):
        """Create a new participant instance."""
        self = cls.__new__(cls)
        await self.__init__(root_hdpriv, name, host, port)
        return self