# Beacon Aggregation Protocols

This is an initial attempt to document the data that is required to be exchanged between participants and a coordinator in order to facilitate a two key beacon aggregation protocols: Establishing a Beacon and Beacon Signal Authorization. This data is based on a proof of concept implementation of the SMTAggregateBeacon algorithms in Jupyter Notebook.

## Communication Protocol



## Establish Beacon Algorithm

Coordinator → **BeaconAdvert** → Broadcast  
Participant → **OptIn** → Coordinator  
Coordinator → **CohortSet** → Participants  
Participant → **DID Registration** → Coordinator  

| Message              | Direction *(actor → actor)* | High-level Purpose                                           |
| -------------------- | --------------------------- | ------------------------------------------------------------ |
| **BeaconAdvert**     | Coordinator → *Broadcast*   | Publicly describes the Beacon’s parameters (cadence, cohort size, fees, comms, etc.) so potential participants can evaluate and join. |
| **OptIn**            | Participant → Coordinator   | Signals a participant’s intent to join the advertised Beacon, proving control of their cohort public key and providing a return-contact channel. |
| **CohortSet**        | Coordinator → Participants  | Confirms the final list of cohort public keys and supplies the derived *n-of-n* P2TR Beacon address, establishing the group’s shared control. |
| **DID Registration** | Participant → Coordinator   | (SMT Beacons only) Registers the set of DIDs a participant will update so the Coordinator can later supply valid inclusion / non-inclusion proofs. |

### BeaconAdvert
| Field | Description |
|-------|-------------|
| Advert ID | Unique per beacon |
| Frequency & Latency | Update cadence and participant response window |
| Cohort Size | Min / Max / Fixed |
| Beacon Type | `CIDAggregateBeacon` or `SMTAggregateBeacon` |
| Financials – Subscription | Recurring‑fee terms |
| Financials – Pay‑per‑Update | Per‑update fee terms |

### OptIn
| Field | Description |
|-------|-------------|
| Advert ID | Beacon being joined |
| Cohort Participation PubKey | Hex Secp256k1 key |
| Signature | From the above key |

### CohortSet
| Field | Description |
|-------|-------------|
| Advert ID | Beacon whose cohort is being set |
| Participant Cohort Keys | Hex public keys for all cohort participants |
| Beacon Address | n‑of‑n P2TR address |

### DID Registration
| Field | Description |
|-------|-------------|
| Beacon Address | Target Beacon |
| Participant PubKey | Identifies participant within Beacon |
| DID(s) | One or more DIDs to be covered by proofs |

## Beacon Signal Authorization
Participant → **Request Aggregation** → Coordinator  
Coordinator → **Authorize Beacon Signal Request** → Participants  
Participant → **MuSig2 Nonce Contribution** → Coordinator  
Coordinator → **Aggregated MuSig2 Nonce** → Participants  
Participant → **Beacon Signal Authorization** → Coordinator  

| Message                             | Direction *(actor → actor)* | High-level Purpose                                           |
| ----------------------------------- | --------------------------- | ------------------------------------------------------------ |
| **Request Aggregation**             | Participant → Coordinator   | Submits the *hash* of a signed DID Update Payload—staking the participant’s desired change for inclusion in the next Beacon signal. |
| **Authorize Beacon Signal Request** | Coordinator → Participants  | Sends the unsigned PSBT that spends the Beacon UTXO (plus any SMT proofs) and asks the cohort to begin a MuSig2 signing session. |
| **MuSig2 Nonce Contribution**       | Participant → Coordinator   | Supplies each participant’s MuSig2 public nonce points for the ongoing signing session. |
| **Aggregated MuSig2 Nonce**         | Coordinator → Participants  | Returns the aggregate of all nonce points so each participant can produce a correct partial signature. |
| **Beacon Signal Authorization**     | Participant → Coordinator   | Delivers the participant’s partial signature over the PSBT, authorizing the final Beacon signal (transaction) once all signatures are collected. |

### Request Aggregation
| Field | Description |
|-------|-------------|
| Beacon Address | Beacon for the update |
| update_hash | Hash of signed DID update |
| DID | DID being updated |
| Participant PubKey | Cohort key of sender |

### Authorize Beacon Signal Request
| Field | Description |
|-------|-------------|
| Session ID | MuSig2 session identifier |
| Beacon Address | Beacon whose UTXO is spent |
| Pending Beacon Signal | Unsigned PSBT with update data in TxOut(`OP_RETURN <hash>` or SMT root) |
| Proofs | Inclusion / non‑inclusion proofs for each registered DID (SMT Beacons only) |

### MuSig2 Nonce Contribution
| Field | Description |
|-------|-------------|
| Session ID | Signing session |
| Beacon Address | Target Beacon |
| nonce points | Hex MuSig2 public nonces |

### Aggregated MuSig2 Nonce
| Field | Description |
|-------|-------------|
| Session ID | Signing session |
| Beacon Address | Target Beacon |
| aggregated nonce points | Hex aggregated nonces |

### Beacon Signal Authorization
| Field | Description |
|-------|-------------|
| Session ID | Signing session |
| Beacon Address | Target Beacon |
| TxSig | Participant’s partial signature over the PSBT |