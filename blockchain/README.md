# Registre Hyperledger Fabric — preuves d'artefacts

## Contrat
- Chaincode : `blockchain/chaincode/` (`createArtifact`, `readArtifact`)
- Refus d'overwrite sur `artifact_id` existant.
- Seules les métadonnées + SHA-256 vont sur chaîne. **Aucun fichier médical brut, aucune identité patient.**

## Mode MOCK (par défaut)
- `FABRIC_MODE=mock`
- Ledger : `data/mock_ledger.json` (écriture atomique).
- `tx_id` préfixé `MOCK-` — **preuve locale simulée, intégration Fabric non démontrée**.

## Mode FABRIC réel
Prérequis : Docker + `fabric-samples/test-network`.
```bash
cd ~/fabric/fabric-samples/test-network
./network.sh up createChannel -c mychannel -ca
./network.sh deployCC -ccn artifact -ccp ~/projet/blockchain/chaincode -ccl javascript