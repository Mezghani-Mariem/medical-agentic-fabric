# MedTrace — interface et validation de Mariem Mezghani

Partie de Mariem Mezghani du projet universitaire **Système Agentique d’Analyse Médicale Sécurisée et Traçable par IA et Hyperledger Fabric**. Cette livraison contient le contrôle des entrées, le masquage simple des rapports, le validateur de prédictions et un dashboard HTML/CSS/JS utilisable indépendamment du backend.

**Prototype pédagogique, non diagnostic. Données synthétiques uniquement.** Les modes et transactions simulés sont toujours affichés comme MOCK. Aucun modèle IA, prétraitement médical, orchestrateur, serveur de prédiction, registre ou chaincode Fabric n’est implémenté dans cette livraison.

## Installation sous Windows 11

Python 3.10 ou plus récent et un navigateur moderne suffisent. Testé ici avec Python 3.12.6. Node.js n’est nécessaire que pour les tests JavaScript supplémentaires ; aucun `npm install` n’est requis. Les modules Python et le dashboard n’ont **aucune dépendance d’exécution**. pytest est la seule dépendance directe de développement.

Dans PowerShell, depuis le dossier du projet :

```powershell
Set-Location 'C:\Users\Lenovo\Desktop\projet_tarek'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-mezghani.txt
.\.venv\Scripts\python.exe -m pytest -q
```

L’utilisation directe de l’exécutable du venv évite de modifier la politique d’exécution PowerShell pour activer un script. Le fichier `requirements-mezghani.txt` reste séparé du `requirements.txt` possédé par Mrabet ; celle-ci pourra inclure `-r requirements-mezghani.txt` dans ses dépendances de développement au merge.

## Démarrer le dashboard autonome

```powershell
Set-Location 'C:\Users\Lenovo\Desktop\projet_tarek'
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

Ouvrir **http://127.0.0.1:5500/frontend/** dans Edge, Chrome ou Firefox. Arrêter le serveur avec `Ctrl+C`. Sans venv, la même commande fonctionne avec `python -m http.server 5500 --bind 127.0.0.1`. Servir la **racine du projet**, pas seulement `frontend/`, pour que le bouton de chargement des échantillons trouve `samples/`. Le double-clic direct sur `index.html` ne suffit pas aux imports JS et aux fixtures HTTP. Le serveur Python est uniquement un serveur statique local de démonstration ; il n’expose aucun endpoint d’analyse.

1. Le mode par défaut est **MOCK · Démonstration**. Cliquer sur **Charger les fichiers de démonstration**, puis **Analyser le dossier**.
2. Consulter les 720 points ECG synthétiques, la classe de démonstration, la confiance de 91 %, le statut `ACCEPTED`, les motifs et l’explication.
3. La table présente huit artefacts, hashes complets, parents, références hors chaîne et transactions préfixées `MOCK-`. Le journal montre les étapes simulées.
4. Cliquer **Vérifier l’intégrité** : réponse simulée `VALID`. Cliquer **Simuler une modification**, puis vérifier de nouveau : `MODIFIED` et empreintes différentes sur `processed`.
5. Changer le scénario pour démontrer la confiance faible (62 %), la mauvaise qualité (`REVIEW_REQUIRED`), l’artefact manquant (`REJECTED`, vérification `MISSING`) ou l’intégrité compromise (`REJECTED`, vérification `MODIFIED`).
6. Ouvrir un dossier antérieur dans l’historique. Les dossiers restent en mémoire de la session ; un rechargement ou un changement de connexion les efface.

Ces scénarios produisent des réponses **préétablies** : aucune prédiction n’est déduite de l’ECG. Les empreintes ne sont pas celles des fichiers importés. La simulation de modification ne modifie aucun fichier. Les contrôles JS ne remplacent pas les fonctions Python qui sont vérifiées séparément. La page affiche explicitement : **« preuve locale simulée, intégration Fabric non démontrée »**.

## Exécuter les modules sans backend

```powershell
.\.venv\Scripts\python.exe -m app.input_checks samples\ecg_valid.csv samples\report_valid.txt
.\.venv\Scripts\python.exe -m app.input_checks samples\ecg_invalid.csv samples\report_valid.txt
.\.venv\Scripts\python.exe -m app.validation
```

Le contrôle affiche `{valid,reasons,report_clean}` en JSON et sort avec code 0 si valide, 1 sinon. La deuxième commande doit échouer proprement. La troisième affiche les décisions pour deux confiances fictives. Le masquage remplace uniquement les champs structurés Nom, Prénom et Patient ID ; les noms dans le texte libre ne sont pas anonymisés.

Les fichiers d’exemple et les fixtures sont déjà livrés. Pour les régénérer de façon déterministe (écrase uniquement nos échantillons et fixtures) :

```powershell
.\.venv\Scripts\python.exe samples\generate_samples.py
```

## Tests

```powershell
# Tous les tests pytest de cette livraison
.\.venv\Scripts\python.exe -m pytest -q

# Seulement les deux modules à transmettre
.\.venv\Scripts\python.exe -m pytest -q tests\test_input_checks.py tests\test_validation.py

# Tests supplémentaires : adaptateurs HTTP, fixtures, erreurs et contrôles JS
node --test frontend/tests/*.test.js
```

Les tests Python couvrent les fichiers vides/mal formés/binaires, UTF-8, tailles limites exactes, valeurs non finies, masquage et idempotence, confiance au seuil et sous le seuil, qualité inconnue, prédictions mal formées, artefacts absents, intégrité compromise et priorité des statuts. Python et JavaScript consomment les 54 mêmes cas CSV, avec comparaison directe des décisions si Node.js est présent ; sinon seul ce test de comparaison est ignoré. Les tests JS couvrent aussi le rendu stable des nombres extrêmes, les huit artefacts et leur lignée, les parcours du contrôleur avec doubles DOM, les cinq scénarios MOCK, ainsi que le véritable transport HTTP multipart vers un **stub local**. Aucun serveur des collègues ni accès Internet n’est nécessaire ; le test HTTP utilise seulement la boucle locale et ferme son serveur.

Le plan manuel et les captures à réaliser se trouvent dans [tests/test_ui_manual.md](tests/test_ui_manual.md). Le compte rendu des vérifications effectivement exécutées est dans [docs/verification.md](docs/verification.md).

## Arborescence de cette livraison

```text
app/
  __init__.py                   package partagé initialisé, sans backend
  input_checks.py               check_inputs + CLI
  validation.py                 validate + démonstration CLI
frontend/
  index.html                    dashboard responsive en français
  style.css                     présentation sans framework ni ressource externe
  app.js                        contrôleur DOM et parcours utilisateur
  api_adapter.js                quatre appels HTTP réels
  mock_api.js                   scénarios simulés isolés, en mémoire
  contracts.js                  contrôles des réponses JSON
  input_preview.js              contrôles navigateur et aperçu du signal brut
  waveform.js                   coordonnées SVG stables, sans traitement médical
  fixtures/                     analyse, historique et vérification MOCK
  tests/*.test.js               adaptateurs, HTTP local, contrôleur, CSV, lignée, rendu
  tests/dom_harness.mjs          doubles DOM ; ne remplace pas un navigateur
  tests/csv_fixtures.mjs         lecteur commun des fixtures et runner de parité
  package.json                  modules ESM ; aucune dépendance npm
samples/
  ecg_valid.csv                 720 valeurs entièrement synthétiques
  ecg_invalid.csv               valeurs non numériques et NaN
  ecg_short.csv                 format valide, 3 points (qualité au backend)
  report_valid.txt              identités fictives à masquer
  report_invalid.txt            contenu binaire interdit
  generate_samples.py           génération réservée aux données de test
  csv_contract_cases.json        54 cas partagés par Python et JavaScript
tests/
  test_input_checks.py
  test_validation.py
  test_frontend_contract.py      cohérence des contrôles DOM, fichiers et fixture
  test_csv_contract.py           fixtures partagées et comparaison Python/JS
  test_dashboard_http.py         démarrage HTTP statique et ressources locales
  test_ui_manual.md
docs/
  api_example.json               réponse exemple au chemin demandé par le guide
  contracts.md                  contrats communs et compléments explicites
  verification.md               résultats constatés et limites
requirements-mezghani.txt        pytest uniquement, dépendance de développement
README.md
```

Les fichiers exclusifs de Mrabet (`main.py`, `preprocess.py`, `predict.py`, `orchestrator.py`, modèles, `requirements.txt`) et Abidi (`hashing.py`, `registry.py`, blockchain, tests du registre) ne sont pas créés ou modifiés. Le dépôt initial était vide ; `app/__init__.py` initialise simplement le package partagé demandé par le guide.

## Intégration pour Mariem Mrabet et Rimeh Abidi

Lire [docs/contracts.md](docs/contracts.md) avant merge. Les signatures et endpoints sont inchangés. **Seul le JSON de l’historique était absent du guide** : une enveloppe `{case_id,events}` est proposée et explicitement documentée, avec des conventions complémentaires pour les cas d’erreur de vérification. S’accorder sur ces détails avant le merge ; leurs gardes sont isolées dans `frontend/contracts.js`.

Le garde impose maintenant un exemplaire de chacun des huit types pour ACCEPTED et REVIEW_REQUIRED, des UUID/types uniques et une lignée causale sans cycle. Les résultats REJECTED peuvent être partiels et sont indiqués INCOMPLET. Le détail des liens autorisés est une proposition explicite à confirmer avec Mrabet. **Les contrôles de complétude et d’intégrité doivent aussi être imposés par son backend.** Le compteur 8/8 indique seulement une structure de métadonnées valide, sans inventer de preuve ou d’artefact.

Mrabet importe `check_inputs` en début de pipeline, renvoie HTTP 422 si invalide, utilise `report_clean` pour les traitements de contexte, puis appelle `validate` avec la qualité et les indicateurs réels. Nos fonctions n’importent aucun module de ses fichiers. Le hachage des octets bruts reste celui spécifié par le guide ; convenir d’une conservation hors chaîne adaptée aux seules données synthétiques.

Quand son backend est disponible, elle peut lancer sa commande **dans sa branche intégrée**, après installation de ses propres dépendances :

```powershell
# Disponible seulement après intégration de la partie Mrabet
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Garder le serveur statique sur 5500 dans un second terminal, choisir **API · Backend réel**, puis configurer l’adresse `http://127.0.0.1:8000`. Les quatre routes `/api/analyze`, `/api/cases/{id}`, `/api/cases/{id}/history` et `/api/cases/{id}/verify` sont alors utilisées. Le backend doit autoriser l’origine `http://127.0.0.1:5500` par CORS, ou servir le frontend lui-même. Les erreurs réelles sont affichées sans fallback MOCK.

Abidi garde son contrat de registre. Le dashboard affiche le `ledger_mode` et les transactions fournis par le backend ; le libellé `FABRIC` n’est jamais généré par l’adaptateur MOCK. Aucun ECG, rapport, label ou texte médical ne doit être stocké sur chaîne. La vraie vérification des fichiers hors chaîne appartient au backend et au registre, pas au navigateur.

## Références techniques

Le parseur Python utilise le module standard [csv](https://docs.python.org/3.12/library/csv.html). Les tests suivent l’invocation officielle [pytest](https://docs.pytest.org/en/stable/getting-started.html). Les décisions de format et de seuil viennent des guides d’équipe, pas d’une recommandation médicale.
