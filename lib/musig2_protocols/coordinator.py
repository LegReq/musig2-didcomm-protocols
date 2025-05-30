import uuid
from typing import List, Dict
from .didcomm_service import DIDCommService
from did_peer_2 import KeySpec, generate
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from aries_askar import Key, KeyAlg
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from .cohort import Musig2Cohort
from .keygen.messages.subscribe import SubscribeMessage
from .keygen.messages.subscribe_accept import SubscribeAcceptMessage
from .keygen.messages.cohort_advert import CohortAdvertMessage
from .keygen.messages.opt_in import CohortOptInMessage
from .keygen.message_types import SUBSCRIBE, OPT_IN
from .context import InMemoryContextStorage
from buidl.ecc import S256Point 

class Coordinator:
    """Coordinates MuSig2 protocol operations between participants."""

    async def __init__(self, name: str, host: str = "localhost", port: int = 8767):
        """Initialize the coordinator with DIDComm messaging service."""
        self.didcomm = DIDCommService(name, host, port)
        self.subscribers: List[str] = []
        self.cohorts: List[Musig2Cohort] = []
        # TODO: Coodinator should be able to have many DIDs
        self.did = await self.generate_did()

        # Register message handlers
        self.didcomm.register_message_handler(
            SUBSCRIBE,
            self._handle_subscribe
        )
        self.didcomm.register_message_handler(
            OPT_IN,
            self._handle_join_cohort
        )

    async def generate_did(self):
        """Generate a DID for the coordinator."""
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
        """Start the coordinator's DIDComm messaging service."""
        await self.didcomm.start_websocket_connection()

    async def _handle_subscribe(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle subscription requests from participants."""
        msg_sender = message["from"]
        if msg_sender not in self.subscribers:
            self.subscribers.append(msg_sender)
            
            # Send subscription acceptance
            accept_msg = SubscribeAcceptMessage(
                to=msg_sender,
                frm=self.did
            )
            await self.didcomm.send_message(
                accept_msg.to_dict(),
                msg_sender,
                self.did
            )

    async def _handle_join_cohort(self, message: Dict, contact_context: InMemoryContextStorage, thread_context: InMemoryContextStorage):
        """Handle join cohort requests from participants."""
        cohort_id = message.get("thread_id")
        participant = message["from"]
        participant_pk = message.get("participant_pk")
        # Find the cohort
        cohort = next((c for c in self.cohorts if c.id == cohort_id), None)
        if cohort and participant not in cohort.participants:
            cohort.participants.append(participant)
            cohort.cohort_keys.append(S256Point.parse(bytes.fromhex(participant_pk)))
            
            # If we have enough participants, we can start the key generation
            if len(cohort.participants) >= cohort.min_participants:  # Minimum 2 participants
                await self._start_key_generation(cohort)

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
                thread_id=cohort.id,
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

    @classmethod
    async def create(cls, name: str, host: str = "localhost", port: int = 8767):
        """Create a new coordinator instance."""
        self = cls.__new__(cls)
        await self.__init__(name, host, port)
        return self 