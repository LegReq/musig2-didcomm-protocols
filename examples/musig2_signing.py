import asyncio
from musig2_protocols.coordinator import Coordinator
from musig2_protocols.beacon_participant import BeaconParticipant
from buidl.hd import HDPrivateKey, secure_mnemonic
from musig2_protocols.protocols.keygen.models.cohort import COHORT_SET_STATUS

async def main():
    fred_mnemonic = secure_mnemonic()
    fred_hdpriv = HDPrivateKey.from_mnemonic(fred_mnemonic)
    lucia_mnemonic = secure_mnemonic()
    lucia_hdpriv = HDPrivateKey.from_mnemonic(lucia_mnemonic)
    alice_mnemonic = secure_mnemonic()
    alice_hdpriv = HDPrivateKey.from_mnemonic(alice_mnemonic)
    bob_mnemonic = secure_mnemonic()
    bob_hdpriv = HDPrivateKey.from_mnemonic(bob_mnemonic)
    charlie_mnemonic = secure_mnemonic()
    charlie_hdpriv = HDPrivateKey.from_mnemonic(charlie_mnemonic)

    # Create instances with explicit ports
    coordinator = await Coordinator.create(
        name="Coordinator", 
        port=8767,
    )
    fred = await BeaconParticipant.create(
        name="Fred", 
        port=8766, 
        root_hdpriv=fred_hdpriv
    )
    lucia = await BeaconParticipant.create(
        name="Lucia", 
        port=8768, 
        root_hdpriv=lucia_hdpriv
    )
    alice = await BeaconParticipant.create(
        name="Alice", 
        port=8769, 
        root_hdpriv=alice_hdpriv
    )
    bob = await BeaconParticipant.create(
        name="Bob", 
        port=8770, 
        root_hdpriv=bob_hdpriv
    )
    charlie = await BeaconParticipant.create(
        name="Charlie", 
        port=8771, 
        root_hdpriv=charlie_hdpriv
    )

    print(f"Coordinator DID: {coordinator.did}")
    print(f"Fred DID: {fred.did}")
    print(f"Lucia DID: {lucia.did}")
    print(f"Alice DID: {alice.did}")
    print(f"Bob DID: {bob.did}")
    print(f"Charlie DID: {charlie.did}")

    # Start the services
    coordinator_task = asyncio.create_task(coordinator.start())
    fred_task = asyncio.create_task(fred.start())
    lucia_task = asyncio.create_task(lucia.start())
    alice_task = asyncio.create_task(alice.start())
    bob_task = asyncio.create_task(bob.start())
    charlie_task = asyncio.create_task(charlie.start())
    # Give the servers time to start up
    await asyncio.sleep(1)

    print("Attempting to subscribe participants to coordinator...")
    # Use the services
    await fred.subscribe_to_coordinator(coordinator.did)
    await asyncio.sleep(0.5)  # Give time for Fred's subscription to process
    await lucia.subscribe_to_coordinator(coordinator.did)
    await asyncio.sleep(0.5)  # Give time for Lucia's subscription to process
    await alice.subscribe_to_coordinator(coordinator.did)
    await asyncio.sleep(0.5)  # Give time for Alice's subscription to process
    await bob.subscribe_to_coordinator(coordinator.did)
    await asyncio.sleep(0.5)  # Give time for Bob's subscription to process
    await charlie.subscribe_to_coordinator(coordinator.did)
    await asyncio.sleep(2)  # Give time for Charlie's subscription to process

    # Wait for all participants to be subscribed
    while len(coordinator.subscribers) < 5:
        print(f"Waiting for all participants to subscribe. Current subscribers: {len(coordinator.subscribers)}")
        await asyncio.sleep(1)

    print("All participants have subscribed. Announcing new cohort...")
    cohort = await coordinator.announce_new_cohort(min_participants=5)


    print(f"Charlie DID: {charlie.did}")
    print(f"Fred DID: {fred.did}")
    print(fred.did == charlie.did)

    fred_request_success = await fred.request_cohort_signature(cohort.id, "Hello, world!")
    while not fred_request_success:
        print(f"Waiting for Fred to request signature for cohort {cohort.id}")
        await asyncio.sleep(1)
        fred_request_success = await fred.request_cohort_signature(cohort.id, "Hello, world!")

    charlie_request_success = await charlie.request_cohort_signature(cohort.id, "Hello, world!")
    while not charlie_request_success:
        print(f"Waiting for Charlie to request signature for cohort {cohort.id}")
        await asyncio.sleep(1)
        charlie_request_success = await charlie.request_cohort_signature(cohort.id, "Hello, world!")



    # await asyncio.sleep(1)
    pending_request_count = len(coordinator.cohorts[0].pending_signature_requests)
    while pending_request_count != 2:
        await asyncio.sleep(1)
        print(f"Pending request count: {pending_request_count}")
        pending_request_count = len(coordinator.cohorts[0].pending_signature_requests)

    print("Starting signing session")
    await coordinator.start_signing_session(cohort.id)


    
    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Cancel the main tasks
        coordinator_task.cancel()
        fred_task.cancel()
        lucia_task.cancel()
        alice_task.cancel()
        bob_task.cancel()
        charlie_task.cancel()
        
        # Clean up connections
        await coordinator.didcomm.cleanup()
        await fred.didcomm.cleanup()
        await lucia.didcomm.cleanup()
        await alice.didcomm.cleanup()
        await bob.didcomm.cleanup()
        await charlie.didcomm.cleanup()
        
        try:
            await coordinator_task
            await fred_task
            await lucia_task
            await alice_task
            await bob_task
            await charlie_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main()) 