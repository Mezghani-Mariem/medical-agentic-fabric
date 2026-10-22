# Medical agentic Fabric university prototype

Shared scaffolding for **Système Agentique d'Analyse Médicale Sécurisée et Traçable par IA et Hyperledger Fabric**.

This is an educational, non-diagnostic prototype. Use synthetic demonstration data only. Never commit patient records, credentials, virtual environments or runtime ledger data. Medical files must remain off chain.

Contributors develop independently on feature branches:

- Mariem Mezghani: `frontend/`, `app/input_checks.py`, `app/validation.py`, related tests, synthetic samples and handoff documentation.
- Mariem Mrabet: API/backend, preprocessing, model and orchestration.
- Rimeh Abidi: hashing, registry adapter, Hyperledger Fabric and chaincode.

The shared package is `app/`. Contributors add only the files in their assigned scope. Agree on the common integration contracts before merging. This initial main branch contains scaffolding only; implementations belong on feature branches.
