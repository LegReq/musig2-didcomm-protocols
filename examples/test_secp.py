"""Example of using DIDComm Messaging."""

from aries_askar import Key, KeyAlg
from didcomm_messaging.crypto.backend.askar import AskarCryptoService, AskarSecretKey
from didcomm_messaging.crypto.backend.basic import InMemorySecretsManager
from didcomm_messaging.packaging import PackagingService
from didcomm_messaging.multiformats import multibase
from didcomm_messaging.multiformats import multicodec
from didcomm_messaging.resolver.peer import Peer2, Peer4
from didcomm_messaging.resolver import PrefixResolver
from did_peer_2 import KeySpec, generate, json

async def generate_did():
    """Generate a DID for the coordinator."""
    verkey = Key.generate(KeyAlg.K256)
    xkey = Key.generate(KeyAlg.K256)

    did = generate(
        [
            KeySpec.verification(
                multibase.encode(
                    multicodec.wrap(
                        "secp256k1-pub",
                        verkey.get_public_bytes()
                    ),
                    "base58btc",
                )
            ),
            KeySpec.key_agreement(
                multibase.encode(
                    multicodec.wrap(
                        "secp256k1-pub",
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
                    "uri": "ws://localhost:8024",
                    "accept": ["didcomm/v2"],
                    "routingKeys": [],
                },
            },
        ],
    )
    secrets = InMemorySecretsManager()
    await secrets.add_secret(AskarSecretKey(verkey, f"{did}#key-1"))
    await secrets.add_secret(AskarSecretKey(xkey, f"{did}#key-2"))
    return did

async def main():
    """An example of using DIDComm Messaging."""
    did = await generate_did()
    print(did)
    resolver = PrefixResolver({"did:peer:2": Peer2(), "did:peer:4": Peer4()})

    document = await resolver.resolve(did)
    print(json.dumps(document, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
