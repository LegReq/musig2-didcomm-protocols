# MuSig2 DIDComm Protocol

This is exploratory work that develops DIDComm protocols to coordinate the MuSig2 cryptographic protocols for key generation and signing specifically for the Bitcoin ecosystem.

A overview of the protocol can be found at [Beacon Aggregation](./beacon_aggregation_protocol.md). Although this is specific to did:btc1, which is the motivation for this work.

## Run the example

Prerequisites (Python 3.8)

1. Create a virtual environment

`python -m venv venv`

2. Activate the virtual environent

`source venv/bin/activate`

3. Install the library from the folder

`pip install -e .`

4. Run the examples

Generate musig2 Bitcoin address with 5 participans
`python examples/musig2_keygen_example.py`

Generate musig2 Bitcoin address with 5 participans and coordinate a spend from that address
 `python examples/musig2_sign.py`






