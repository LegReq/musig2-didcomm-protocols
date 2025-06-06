import json
from aries_askar import Key, KeyAlg
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from didcomm_messaging.crypto.backend.basic import InMemorySecretsManager
from didcomm_messaging.packaging import PackagingService
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from didcomm_messaging.resolver.peer import Peer2, Peer4
from didcomm_messaging.resolver import PrefixResolver
from did_peer_2 import KeySpec, generate, json
from didcomm_messaging import DIDCommMessaging
from didcomm_messaging.routing import RoutingService
from pydid.did import DID
import websockets
import asyncio
from collections import defaultdict
from .router import MessageRouter
import aiojobs


class DIDCommService:

    def __init__(self, name: str, host: str, port: int, tls: bool = False):
        self.name = name
        self.host = host
        self.port = port
        self.didcomm_websocket_url = f"ws://{host}:{port}"
        self.tls = tls
        self.crypto = AskarCryptoService()
        self.secrets = InMemorySecretsManager()
        self.resolver = PrefixResolver({"did:peer:2": Peer2(), "did:peer:4": Peer4()})
        self.packaging = PackagingService()
        self.routing = RoutingService()
        self.didcomm_messaging = DIDCommMessaging(
            crypto=self.crypto,
            secrets=self.secrets,
            resolver=self.resolver,
            packaging=self.packaging,
            routing=self.routing,
        )
        
        # Initialize message router with a scheduler
        self.scheduler = aiojobs.Scheduler()
        self.message_router = MessageRouter(self.scheduler)
        
        # Store active websocket connections
        self.connections = {}
        # Message queues for each peer
        self.message_queues = defaultdict(asyncio.Queue)
        # Lock for connection management
        self.connection_locks = defaultdict(asyncio.Lock)
        # Track connection status
        self.connection_status = defaultdict(bool)

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
        await self.secrets.add_secret(AskarSecretKey(verkey, f"{did}#key-1"))
        await self.secrets.add_secret(AskarSecretKey(xkey, f"{did}#key-2"))
        return did

    async def get_connection(self, endpoint: str):
        """Get or create a websocket connection to an endpoint."""
        async with self.connection_locks[endpoint]:
            if endpoint not in self.connections:
                try:
                    print(f"{self.name}: Creating new connection to {endpoint}")
                    self.connections[endpoint] = await websockets.connect(endpoint)
                    self.connection_status[endpoint] = True
                    print(f"{self.name}: Successfully connected to {endpoint}")
                except Exception as e:
                    print(f"{self.name}: Error connecting to {endpoint}: {str(e)}")
                    self.connection_status[endpoint] = False
                    raise
            return self.connections[endpoint]

    async def send_message(self, message, to, frm):
        print(f"{self.name}: Preparing to send message to {to}")
        packy = await self.didcomm_messaging.pack(
            message=message,
            to=to,
            frm=frm,
        )
        packed = packy.message            
        endpoint = packy.get_endpoint("ws")
        print(f"{self.name}: Got endpoint {endpoint} for message to {to}")
        
        # Add message to queue
        await self.message_queues[endpoint].put((packed, message))
        print(f"{self.name}: Added message to queue for {endpoint}")
        
        # Process message queue if not already running
        if not hasattr(self, f"_queue_processor_{endpoint}"):
            print(f"{self.name}: Starting queue processor for {endpoint}")
            setattr(self, f"_queue_processor_{endpoint}", asyncio.create_task(
                self._process_message_queue(endpoint)
            ))

    async def _process_message_queue(self, endpoint):
        """Process messages in the queue for a specific endpoint."""
        print(f"{self.name}: Starting message queue processor for {endpoint}")
        while True:
            try:
                packed, original_message = await self.message_queues[endpoint].get()
                print(f"{self.name}: Processing message from queue for {endpoint}")
                
                websocket = await self.get_connection(endpoint)
                if not self.connection_status[endpoint]:
                    print(f"{self.name}: Connection to {endpoint} is not active, retrying...")
                    await asyncio.sleep(1)
                    continue
                
                print(f"{self.name}: Sending message to {endpoint}")
                await websocket.send(packed)
                
                # print(f"{self.name}: Waiting for response from {endpoint}")
                # response = await websocket.recv()
                # print(f"{self.name}: Received response from {endpoint}: {response}")
                self.message_queues[endpoint].task_done()
            except Exception as e:
                print(f"{self.name}: Error processing message queue for {endpoint}: {str(e)}")
                self.connection_status[endpoint] = False
                # If connection is closed, remove it so it will be recreated
                if endpoint in self.connections:
                    del self.connections[endpoint]
                await asyncio.sleep(1)  # Wait before retrying

    def register_message_handler(self, message_type: str, handler):
        """Register a handler function for a specific message type."""
        print(f"{self.name}: Registering handler for message type {message_type}")
        self.message_router.add_route(message_type, handler)

    def remove_message_handler(self, message_type: str):
        """Remove a handler for a specific message type."""
        print(f"{self.name}: Removing handler for message type {message_type}")
        if message_type in self.message_router.routes:
            del self.message_router.routes[message_type]

    async def handle_messages(self, websocket):
        print(f"{self.name}: New client connected")
        try:
            async for packed_message in websocket:
                print(f"{self.name}: Received raw message")
                try:
                    unpacked = await self.didcomm_messaging.packaging.unpack(
                        self.crypto, self.resolver, self.secrets, packed_message
                    )
                    msg = json.loads(unpacked[0].decode())
                    print(f"{self.name}: Successfully unpacked message: {json.dumps(msg, indent=2)}")

                    # Route the message using MessageRouter
                    await self.message_router.route_message(msg)
                except Exception as e:
                    print(f"{self.name}: Error processing message: {str(e)}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"{self.name}: Connection closed: {str(e)}")

    async def start_websocket_connection(self):
        print(f"{self.name}: Starting websocket server on {self.didcomm_websocket_url}")
        async with websockets.serve(self.handle_messages, self.host, self.port):
            print(f"{self.name}: WebSocket server started successfully")
            await asyncio.Future()  # Run forever

    async def cleanup(self):
        """Clean up all connections and queues."""
        print(f"{self.name}: Cleaning up connections and queues")
        for endpoint, websocket in self.connections.items():
            try:
                await websocket.close()
                print(f"{self.name}: Closed connection to {endpoint}")
            except Exception as e:
                print(f"{self.name}: Error closing connection to {endpoint}: {str(e)}")
        self.connections.clear()
        self.message_queues.clear()
        self.connection_status.clear()