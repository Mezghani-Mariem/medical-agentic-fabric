# Contrats d’intégration de Mariem Mezghani

Source de vérité : `04_Guide_Integration.docx`, complété par `01_Mariem_Mezghani.docx`. Les guides de Mrabet et Abidi ont été lus pour respecter leurs frontières de propriété. Le cahier des charges original n’a pas été fourni séparément. Les conventions supplémentaires ci-dessous sont explicitement identifiées ; aucune API partagée n’a été renommée.

## Modules Python livrés

```python
from app.input_checks import check_inputs
from app.validation import validate

checked = check_inputs(ecg_bytes, report_bytes)
# {"valid": bool, "reasons": list[str], "report_clean": str}

decision = validate(prediction, quality, artifacts_ok=True,
                    integrity_ok=True, report_text=checked["report_clean"])
# {"status": "ACCEPTED|REVIEW_REQUIRED|REJECTED", "reasons": list[str]}
```

Ces fonctions sont pures : aucun accès disque, appel réseau, stockage, modèle ou registre. Les messages sont en français ; les constantes de statut restent exactement celles du guide. Aucun texte de fichier ni identifiant fourni n’est recopié dans les erreurs de contrôle.

### Contrôle des entrées

| Élément | Règle |
| --- | --- |
| Arguments | `bytes` ; les valeurs d’autres types produisent `valid=False` |
| ECG | Maximum inclusif **2 097 152 octets** (2 Mio), UTF-8 strict avec BOM facultatif |
| Format CSV | Virgule, colonne exacte `signal`, en-tête unique et sans colonne vide, lignes de largeur cohérente |
| Signal | Au moins une valeur décimale ou scientifique, finie ; `NaN`, infinis, chaînes, valeurs vides et nombres avec `_` refusés |
| Rapport | Maximum inclusif **65 536 octets** (64 Kio), UTF-8 strict, texte non vide |
| Texte binaire | NUL et contrôles C0/DEL refusés, sauf tabulation, CR et LF |
| Masquage | Champs entiers `Nom`, `Prénom`/`Prenom`, `Patient ID` en début de ligne, sans distinction de casse ; espaces, `:` ou `=` acceptés ; variantes `Patient_ID` et `Patient-ID` aussi |
| Substitution | La valeur de chaque champ est remplacée par `[MASQUÉ]` ; le libellé et les autres lignes sont conservés |
| Échec | `report_clean=""`, aucun contenu partiellement nettoyé renvoyé |

Précisions défensives de cette livraison : doublons d’en-têtes et lignes irrégulières refusés ; maximum explicite de **131 072 caractères Unicode décodés par champ**, y compris l’en-tête. La limite est inclusive et compte les guillemets doublés après déquotage comme un seul caractère, et un caractère hors BMP comme un seul caractère. Python utilise `csv.reader(..., strict=True)` et ne modifie pas sa limite globale ; conserver la limite standard du lecteur (131 072), sans la réduire dans le backend. Notre borne explicite reste appliquée même si une autre bibliothèque augmente cette limite globale.

Les colonnes supplémentaires sont autorisées. **Une ligne vide avant l’en-tête est invalide** ; les lignes totalement vides après l’en-tête sont ignorées. Une ligne contenant des espaces ou un signal entre guillemets vide n’est pas une ligne vide. LF, CRLF et CR sont acceptés ; les retours de ligne à l’intérieur d’un champ entre guillemets sont conservés. Des espaces après le guillemet fermant sont refusés par le mode strict. Un guillemet à l’intérieur d’un champ non cité reste un caractère littéral, comme dans Python.

Les contrôles JS reproduisent aussi `str.strip()` de Python, notamment U+0085 ; U+FEFF n’est pas un espace à supprimer dans une valeur. Un seul BOM initial est retiré, sans double suppression entre le décodeur et le parseur. Les décisions Python/JS sont comparées sur les **54 cas partagés** de `samples/csv_contract_cases.json` par `tests/test_csv_contract.py` ; les deux suites les évaluent également séparément. Les contrôles n’effectuent aucune normalisation médicale du signal ni extraction de caractéristiques.

Le minimum de **30 points**, la qualité et la normalisation sont sous la responsabilité de `app/preprocess.py` de Mrabet. `ecg_short.csv` est donc valide en format, mais sa qualité doit être refusée par le prétraitement réel. Les extensions et noms MIME ne sont pas disponibles dans cette signature : le navigateur vérifie `.csv`/`.txt`, et le backend doit vérifier les noms/extensions s’il veut imposer cette règle côté serveur.

Le masquage est une pseudonymisation élémentaire sans table de correspondance : aucune garantie d’anonymat du texte libre, des autres colonnes CSV ou des métadonnées. Les données synthétiques sont obligatoires.

### Validation et priorité

1. `REJECTED` si une prédiction est absente, un artefact manque ou l’intégrité échoue.
2. Sinon `REVIEW_REQUIRED` si `quality.valid=False` ou `confidence < 0.75`.
3. Sinon `ACCEPTED`. Une confiance exactement égale à `0.75` est acceptée.

Précisions pour les entrées mal formées, non définies dans le guide : un label manquant/vide, une confiance absente, booléenne, non numérique, non finie ou hors `[0,1]` est une prédiction invalide et donne `REJECTED`. Une qualité absente ou dont `valid` n’est pas le booléen `True` donne `REVIEW_REQUIRED`. Des indicateurs d’artefact/intégrité différents du booléen `True` donnent `REJECTED`. Les motifs de rejet et de revue sont tous conservés, sans doublons. Le modèle et sa version doivent être présents dans la réponse REST ; cette fonction vérifie seulement le label et la confiance utilisés dans ses règles.

Si `report_text` est non vide, le motif informatif `Cohérence texte/ECG non évaluée automatiquement` est ajouté, sans changer le statut. Le validateur ne fait aucune vérification médicale du rapport. Les indicateurs `artifacts_ok` et `integrity_ok` doivent être calculés par le backend/registre réel ; leurs valeurs par défaut ne constituent pas une preuve d’intégrité.

## REST partagé sans modification

| Méthode | Route | Corps / résultat |
| --- | --- | --- |
| POST | `/api/analyze` | `multipart/form-data`, champs fichiers `ecg` et `report` ; réponse analyse ci-dessous |
| GET | `/api/cases/{case_id}` | Même schéma analyse |
| GET | `/api/cases/{case_id}/history` | Enveloppe d’historique proposée ci-dessous |
| POST | `/api/cases/{case_id}/verify` | Aucun corps ; schéma de vérification du guide |

Une analyse crée un UUID `case_id`. Le navigateur laisse le navigateur définir l’en-tête multipart et sa boundary ; ne pas ajouter `Content-Type: application/json` à cet upload. Les réponses d’erreur acceptées par l’adaptateur sont `{"detail":"message"}`, le `detail` liste standard de FastAPI, ou `{"reasons":["message"]}`. Le backend doit répondre HTTP **422** à un contrôle d’entrée négatif.

Le bloc suivant illustre les clés et **un seul élément** d’artefact ; il ne constitue pas une réponse ACCEPTED complète. Le JSON complet exécutable avec les **huit** artefacts est [api_example.json](api_example.json).

```json
{
  "case_id": "<uuid>",
  "prediction": {
    "label": "demo_class_A",
    "confidence": 0.91,
    "model_name": "<nom>",
    "model_version": "v1"
  },
  "validation": {"status": "ACCEPTED", "reasons": []},
  "explanation": "<texte>",
  "artifacts": [{
    "artifact_id": "<uuid>",
    "type": "raw_ecg",
    "sha256": "<64 caractères hexadécimaux minuscules>",
    "parent_id": null,
    "storage_ref": "data/cases/<case_id>/<artifact_id>.bin",
    "tx_id": "<identifiant renvoyé par le registre>"
  }],
  "ledger_mode": "MOCK"
}
```

Types d’artefact attendus : `raw_ecg`, `raw_report`, `processed`, `features`, `prediction`, `validation`, `explanation`, `final`. L’interface affiche l’ID, le parent, le hash complet, la référence hors chaîne et la transaction de chaque artefact. Les champs supplémentaires sont tolérés. Les UUID, hashes, statuts et types obligatoires sont contrôlés à réception. `prediction: null` est une extension explicite supportée pour un résultat `REJECTED` dû à une prédiction absente ; les succès gardent le schéma du guide. Le préfixe `MOCK-` est utilisé **uniquement par notre adaptateur de démonstration** ; l’adaptateur réel accepte tout `tx_id` non vide avec son `ledger_mode` explicite.

### Schéma exact de réponse d’analyse

| Clé requise | Type et contrainte |
| --- | --- |
| `case_id` | Chaîne UUID canonique 8-4-4-4-12 ; correspond au dossier demandé lors d’un GET |
| `prediction` | Objet `{label: string non vide, confidence: number fini de 0 à 1, model_name: string non vide, model_version: string non vide}` ; ou `null` uniquement si REJECTED selon l’extension documentée |
| `validation` | Objet `{status: ACCEPTED ou REVIEW_REQUIRED ou REJECTED, reasons: string[]}` |
| `explanation` | Chaîne de texte |
| `artifacts` | Tableau d’objets suivant les six champs ci-dessous et la politique de complétude |
| `ledger_mode` | Chaîne exacte `MOCK` ou `FABRIC`, indépendamment du mode de transport API |

Chaque artefact requiert `artifact_id` (UUID), `type` (une des huit constantes), `sha256` (64 hexadécimaux minuscules), `parent_id` (UUID ou null), `storage_ref` (chaîne non vide), `tx_id` (chaîne non vide). Les UUID sont comparés sans distinction de casse pour les doublons et liens parent. Aucun enregistrement manquant n’est fabriqué par le frontend.

### Complétude et lignée V1 — politique frontend à confirmer au merge

La liste des huit types vient du guide. Le guide ne fige pas tous les liens parent exacts : les règles de lignée ci-dessous sont une **proposition d’intégration explicite**, implémentée dans `assertArtifacts` ; aucun champ JSON ni signature partagé n’est ajouté.

- Une réponse `ACCEPTED` **ou** `REVIEW_REQUIRED` doit contenir exactement une occurrence de chacun des huit types. L’ordre du tableau est libre. Une réponse de succès incomplète provoque une erreur de contrat avant son affichage et conserve le dossier précédent avec un message explicite.
- Une réponse `REJECTED` peut contenir de zéro à huit artefacts cohérents. L’interface indique `INCOMPLET · n/8 MÉTADONNÉES` si nécessaire ; elle ne la transforme jamais en résultat accepté. La vérification est désactivée si le tableau est vide.
- Dans tous les statuts, les IDs et types sont uniques ; IDs, hashes et références doivent être bien formés. Tout parent non nul doit exister dans la réponse. Auto-références, doublons d’UUID même avec une casse différente, cycles et parents absents sont refusés.
- L’ordre causal des types est `raw_ecg < raw_report < processed < features < prediction < validation < explanation < final`. Un parent doit appartenir à un type **antérieur** à son enfant. Cela interdit aussi les cycles, indépendamment de l’ordre du tableau.
- `raw_ecg` est racine ; `raw_report` peut être une seconde racine ou un enfant de `raw_ecg`. Un artefact dérivé doit avoir un parent. Les branches causales sont autorisées ; il n’est pas imposé que chaque parent soit le type immédiatement précédent. Les deux fichiers sources peuvent donc avoir deux racines, sans inventer une dépendance entre eux.

Le compteur `MÉTADONNÉES 8/8 · STRUCTURE CONTRÔLÉE` signifie seulement que ces métadonnées satisfont le garde local. **Il ne prouve ni la présence des octets hors chaîne, ni leurs hashes, ni une transaction blockchain réelle.** Le bouton `/verify` et ses résultats restent séparés. Le MOCK « artefact manquant » possède huit enregistrements de métadonnées, mais simule l’absence des octets de `processed` ; sa validation reste REJECTED et son contrôle MISSING.

**Mrabet doit également imposer ces contrôles côté backend**, ainsi que la présence réelle des fichiers attendus, la cohérence avec les preuves initiales du registre et l’exhaustivité du pipeline. Le navigateur est contournable. Ne pas laisser les paramètres par défaut `artifacts_ok=True` / `integrity_ok=True` remplacer les contrôles effectifs. Si le backend choisit une autre lignée valide, convenir d’un changement explicite du garde avant merge.

### Historique — convention proposée, à transmettre à Mrabet

Le guide nomme la route sans fixer son JSON. Cette proposition reste isolée dans `frontend/contracts.js:assertHistory` et le rendu `frontend/app.js:loadHistory`. Une autre forme côté backend doit être convenue avec Mrabet, puis adaptée à cet endroit ; aucun format n’est deviné silencieusement.

```json
{
  "case_id": "<uuid>",
  "events": [{
    "timestamp": "2026-10-22T09:00:00Z",
    "stage": "prediction",
    "status": "MOCK",
    "details": "Description de l’étape",
    "artifact_id": "<uuid, facultatif>",
    "tx_id": "<transaction, facultatif>"
  }]
}
```

`events` est ordonné chronologiquement. Les quatre premiers champs d’événement sont requis ; `status` est le statut de l’événement et n’est pas limité aux trois statuts de validation. `timestamp` est ISO-8601 avec fuseau, idéalement UTC. L’affichage utilise le fuseau local du navigateur. L’indisponibilité de l’historique n’efface pas une analyse valide.

### Vérification — schéma du guide, conventions des erreurs explicites

```json
{
  "case_id": "<uuid>",
  "overall_status": "MODIFIED",
  "checks": [{
    "artifact_id": "<uuid>",
    "status": "MODIFIED",
    "expected_sha256": "<hash initial>",
    "actual_sha256": "<hash recalculé>"
  }]
}
```

Statuts exacts : `VALID`, `MODIFIED`, `MISSING`, `UNVERIFIABLE`. Conventions proposées là où le guide ne précise pas : un résultat par artefact ; `actual_sha256=null` pour un fichier manquant ; `expected_sha256=null` si la preuve de référence est indisponible (`UNVERIFIABLE`) ; priorité agrégée `MODIFIED > MISSING > UNVERIFIABLE > VALID`. Un résultat incomplet ou incohérent est affiché `UNVERIFIABLE`, jamais vert. Le backend doit renvoyer `VALID` seulement si toutes les preuves et fichiers ont effectivement été vérifiés. Le frontend ne recalcule pas les empreintes des fichiers distants.

Une vérification ultérieure ne réécrit pas le statut initial de validation : celui-ci est historique. Une modification signalée apparaît clairement dans le badge global, les lignes d’artefact et le message du contrôle.

## Séparation MOCK / intégration réelle

- `frontend/mock_api.js` utilise `frontend/fixtures/demo_case.json`. Prédictions, événements, hashes et transactions sont simulés, en mémoire de session. Aucun service AI, fichier `.bin`, hachage de téléversement ou registre n’est exécuté.
- Les hashes de fixture identifient des chaînes factices dans `samples/generate_samples.py` ; ils **ne prouvent pas** l’intégrité des fichiers choisis. Le bouton de modification change uniquement un état de scénario MOCK. Recharger la page efface tous ces dossiers.
- Les contrôles JS sont un confort pour l’utilisateur ; **le mode MOCK n’exécute pas les fonctions Python**. Tester ces dernières par pytest ou par leurs commandes CLI. Le mode API doit les appeler côté serveur.
- `frontend/api_adapter.js` exécute les quatre appels HTTP exacts. Aucun fallback silencieux. L’URL par défaut est `http://127.0.0.1:8000`, modifiable dans l’interface ; délai par requête 30 secondes.
- Les données choisies restent en mémoire du navigateur jusqu’au clic sur Analyser en mode API. Les réponses JSON sont rendues via `textContent` et des nœuds DOM, sans HTML fourni par l’API. Aucun stockage local persistant, outil analytique ou ressource externe.

## Handoff backend et registre

Mrabet : importer nos deux fonctions ; arrêter le pipeline avec HTTP 422 si `valid=False` ; transmettre **`report_clean`** aux étapes de contexte, explication et modèle éventuel. Les octets originaux restent disponibles pour la règle de hachage brut, selon la politique de stockage des données synthétiques décidée par l’équipe. Ne jamais envoyer les identités au registre. Définir ensemble la politique de conservation hors chaîne du rapport brut, sans remplacer silencieusement les octets dont l’empreinte est annoncée comme brute.

Pour `validate`, fournir la qualité issue du prétraitement et les indicateurs effectivement calculés. Retourner les clés exactes ci-dessus ; implémenter la convention d’historique proposée, ou convenir d’un adaptateur avant merge. Activer CORS pour `http://127.0.0.1:5500` si le frontend est servi séparément (et `http://localhost:5500` si utilisé). Autoriser GET et POST. Autrement, servir `frontend/` depuis FastAPI et configurer l’URL du même origin dans le formulaire.

Abidi : aucun changement demandé à `record_artifact(record)` / `get_artifact(artifact_id)` ni à `ArtifactRecord`. Les enregistrements du registre restent des métadonnées et hashes ; aucune donnée médicale brute n’y est ajoutée. Le backend doit récupérer les références de registre et comparer les octets hors chaîne pour implémenter le vrai `/verify`.

Contrat interne consommé par Mrabet, sans implémentation dans cette livraison :

```python
from app.input_checks import check_inputs
from app.validation import validate
# Fourni par Abidi, dans sa branche :
from app.registry import record_artifact, get_artifact

checked = check_inputs(ecg_bytes, report_bytes)
# Si checked["valid"] est False : arrêt et HTTP 422.
# Prédiction et quality fournis par les modules de Mrabet.
decision = validate(prediction, quality,
                    artifacts_ok=actual_artifacts_ok,
                    integrity_ok=actual_integrity_ok,
                    report_text=checked["report_clean"])

receipt = record_artifact(record)  # {"tx_id": str, "ledger_mode": "MOCK|FABRIC"}
entry = get_artifact(artifact_id)  # ArtifactRecord ou None
```

`ArtifactRecord` d’Abidi conserve les clés `artifact_id`, `case_id`, `type`, `sha256`, `created_at` (UTC ISO-8601), `version` (`v1`), `parent_id`, `storage_ref`, `created_by` (`orchestrator`). Les UUID, types et hashes correspondent à ceux exposés par REST. Mrabet joint le reçu `tx_id` aux six champs d’artefact affichés et restitue le vrai `ledger_mode`. Abidi fournit le hash initial et le reçu ; Mrabet lit les octets hors chaîne pour la vérification. Aucun ECG, rapport, label ou texte médical ne doit entrer dans le registre.

Canonicalisation conservée pour les modules des collègues : JSON UTF-8 `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, SHA-256 des octets canonisés ; ECG/TXT bruts, SHA-256 des octets d’origine. Aucun module de hachage de production n’est livré ici.

## Limites et vérification finale

Le rendu ECG utilise une échelle de dessin stable avant soustraction, avec coordonnées bornées. Le fichier brut n’est pas modifié ; au plus 800 points sont prévisualisés. Une prévisualisation mal formée est remplacée par un aperçu indisponible, sans propager NaN/Infinity au SVG.

Le MOCK conserve des réponses préétablies en mémoire, sans appel des fonctions Python, modèle, stockage médical ni registre réel. Les dossiers disparaissent au rechargement. Les données de démonstration, hashes et transactions ne sont pas des preuves cryptographiques. La pseudonymisation reste un masquage de champs structurés, pas une anonymisation de texte libre.

Les résultats finaux exécutés, les commandes et les limites de tests sont dans [verification.md](verification.md). Les contrôles DOM de la suite JS utilisent des doubles de test et ne remplacent pas un navigateur. Les captures, le rendu responsive, les sélecteurs de fichiers, l’accessibilité et CORS doivent encore être vérifiés selon [test_ui_manual.md](../tests/test_ui_manual.md). Le backend médical et Hyperledger Fabric réels restent non testés.
