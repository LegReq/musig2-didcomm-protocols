from typing import List, Dict
from .didcomm_service import DIDCommService
from did_peer_2 import KeySpec, generate
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from aries_askar import Key, KeyAlg
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from .keygen.messages.subscribe import SubscribeMessage
from .keygen.messages.subscribe_accept import SubscribeAcceptMessage
from .keygen.messages.cohort_advert import CohortAdvertMessage
from .keygen.messages.opt_in import CohortOptInMessage
from .cohort import Musig2Cohort, COHORT_OPTED_IN
from .keygen.message_types import SUBSCRIBE_ACCEPT, COHORT_ADVERT, COHORT_SET
from .context import InMemoryContextStorage
from buidl.hd import HDPrivateKey

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
        self.did = await self.generate_did()

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

    def get_beacon_key(self, index: int = None):
        """Get the beacon key for a given index."""
        if index is None:
            index = self.next_beacon_key_index
            self.next_beacon_key_index += 1
        return self.root_hdpriv.get_private_key(index)

    async def generate_did(self):
        """Generate a DID for the participant."""
        verkey = Key.generate(KeyAlg.ED25519)
        xkey = Key.generate(KeyAlg.X25519)

        did = generate(
            [
                KeySpec.verification(
                    multibase.encode(
                        multicodec.wrap(
                            "ed25519-pub",
                            verkey.get_public_bytes()
                        ),
                        "base58btc",
                    )
                ),
                KeySpec.key_agreement(
                    multibase.encode(
                        multicodec.wrap(
                            "x25519-pub",
                            xkey.get_public_bytes()
                        ),
                        "base58btc"
                    )
                ),
            ],
            [
                {
                    "type": "DIDCommMessaging",
                    "serviceEndpoint": {
                        "uri": self.didcomm.didcomm_websocket_url,
                        "accept": ["didcomm/v2"],
                        "routingKeys": [],
                    },
                },
            ],
        )

        await self.didcomm.secrets.add_secret(AskarSecretKey(verkey, f"{did}#key-1"))
        await self.didcomm.secrets.add_secret(AskarSecretKey(xkey, f"{did}#key-2"))
        return did

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
        cohort_id = message.get("thread_id")
        btc_network = message.get("btc_network")
        frm = message.get("from")
        if frm not in self.coordinator_dids:
            print(f"BeaconParticipant {self.did} received unsolicited new cohort announcement from {frm}")
            return
        
        cohort = Musig2Cohort(id=cohort_id, btc_network=btc_network)
        self.cohorts.append(cohort)
        # May configure additional rules or await user input to join the cohort
        # Automatically join the new cohort
        await self.join_cohort(cohort.id, message["from"])

    async def _handle_cohort_set(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle cohort set messages from coordinators."""
        cohort_id = message.get("thread_id")
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        cohort_key_state = self.cohort_key_state[cohort_id]
        participant_pk = self.get_beacon_key(cohort_key_state.key_index).point.sec().hex()
        beacon_address = message.get("beacon_address")
        cohort_keys = message.get("cohort_keys")
        cohort.validate_cohort([participant_pk], cohort_keys, beacon_address)
        print(f"BeaconParticipant {self.did} validated cohort {cohort_id} with beacon address {beacon_address}")


    async def join_cohort(self, cohort_id: str, coordinator_did: str):
        """Join a specific cohort."""
        print(f"BeaconParticipant {self.did} joining cohort {cohort_id} with coordinator {coordinator_did}")
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)

        if cohort is not None:
            key_index = self.next_beacon_key_index
            participant_pk = self.get_beacon_key().point.sec().hex()
            cohort_key_state = CohortKeyState(cohort_id, self.did, key_index)
            self.cohort_key_state[cohort_id] = cohort_key_state

            msg = CohortOptInMessage(
                to=coordinator_did,
                frm=self.did,
                thread_id=cohort_id,
                participant_pk=participant_pk
            )
            await self.didcomm.send_message(
                msg.to_dict(),
                coordinator_did,
                self.did
            )
            cohort.status = COHORT_OPTED_IN

    @classmethod
    async def create(cls, root_hdpriv: HDPrivateKey, name: str, host: str = "localhost", port: int = 8766):
        """Create a new participant instance."""
        self = cls.__new__(cls)
        await self.__init__(root_hdpriv, name, host, port)
        return self