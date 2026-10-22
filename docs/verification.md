# Vérifications exécutées

Date : **22 octobre 2026 — passe corrective finale**. Dossier de travail : `C:\Users\Lenovo\Desktop\projet_tarek`. Cette passe corrige les trois constats de la revue initiale. Aucun fichier appartenant à Mrabet ou Abidi n’a été créé, remplacé ou modifié. Les signatures Python et les quatre routes REST restent inchangées. La politique de lignée client est explicitement documentée comme proposition à confirmer au merge.

## Installation et tests

- Python **3.12.6** sous Windows ; création d’un environnement `.venv`.
- Installation de `requirements-mezghani.txt` réussie dans le venv, avec **pytest 9.1.1**. L’environnement demandait une autorisation réseau pour le téléchargement ; aucun changement de configuration système.
- `.\.venv\Scripts\python.exe -m pytest -q` : **145 tests réussis, zéro ignoré**, dont les 89 tests antérieurs, 54 cas partagés, une comparaison directe Python/JS et un démarrage HTTP statique.
- `node --test frontend/tests/*.test.js` : **111 tests réussis, zéro ignoré**, sans dépendance npm. Les sept tests antérieurs restent inclus ; régressions du tracé, du CSV et des artefacts, parcours du contrôleur avec doubles DOM et vrai transport HTTP vers un stub local s’y ajoutent.
- Le test de parité Python lance réellement Node et compare les décisions sur tous les 54 cas. Si Node manque sur une autre machine, seul ce test est explicitement ignoré ; les tests Python de fixtures continuent de fonctionner. Node **22.16.0** était disponible ici.
- Audit différentiel supplémentaire : **5 000 CSV synthétiques générés avec graine fixe**, zéro différence de décision entre JS et Python. Cette vérification locale est distincte du nombre de tests maintenus ci-dessus.
- Vérification syntaxique `node --check` de `app.js`, `input_preview.js` et `contracts.js` : réussie.
- CLI de contrôle avec les échantillons valides : `valid=true`, les trois identifiants fictifs sont masqués, sortie 0.
- CLI de contrôle avec `ecg_invalid.csv` : `valid=false`, motif de valeur non numérique, `report_clean=""`, sortie 1 attendue.
- CLI du validateur : un résultat `ACCEPTED` et un résultat `REVIEW_REQUIRED` sur deux confiances de démonstration.

Les tests n’utilisent aucun module des collègues. Aucun modèle, entraînement, prétraitement médical, registre ou service Fabric n’a été exécuté. Les tests d’adaptateur utilisent des réponses contrôlées et un stub HTTP réel sur boucle locale ; ce ne sont pas des preuves d’un backend médical ou registre réel. Aucune nouvelle dépendance n’a été nécessaire.

## Régressions corrigées et vérifiées

| Sujet | Mise en œuvre et résultat observé |
| --- | --- |
| Débordement du tracé | Mise à l’échelle par la valeur absolue maximale avant toute soustraction. Pour `[-1e308, 1e308]`, sortie exacte `0,145 800,25`. Tests avec `Number.MAX_VALUE`, sous-normaux, zéro, signal constant et données mal formées ; coordonnées finies et bornées, aperçu invalide neutralisé sans exception. |
| CSV cohérent | Ligne vide avant en-tête refusée ; lignes vides de données ignorées ; limite de champ inclusive 131 072 caractères Unicode ; guillemets/CRLF/multiligne, BOM unique, U+0085 et U+FEFF alignés. Les fixtures ASCII, Unicode hors BMP et guillemets doublés testent les limites exactes. |
| Complétude des artefacts | ACCEPTED et REVIEW_REQUIRED sans les huit types sont refusés avant rendu ; IDs/types dupliqués, cycles, références absentes, racine dérivée et ordre causal inverse refusés. Tableau réordonné et deux sources racines supportés. REJECTED partiel affiché INCOMPLET, sans fabrication ; bouton verify désactivé pour zéro artefact. |
| Régression UI logique | Chargement des fichiers, 720 points, prédiction/91%/statut, huit métadonnées, historique, dossiers précédents, cinq scénarios, VALID→MODIFIED, erreurs de vérification, refus d’un faux VALID vide, double clic et réactivation des boutons passent avec doubles DOM. |
| Compatibilité API réelle | `ApiAdapter` utilise `fetch` natif contre un serveur fixture local : quatre routes/méthodes exactes, boundary multipart et fichiers `ecg`/`report`, garde de réponse complet, historique, verify sans corps et HTTP 404 vérifiés. Serveur fermé après le test. |

Les doubles DOM vérifient les liaisons et gestionnaires du contrôleur ; ils ne calculent pas une mise en page et ne simulent pas la politique CORS du navigateur. Le contrôle 8/8 porte sur les métadonnées, pas sur la présence ou l’intégrité des octets distants.

## Démarrage HTTP vérifié

Le test maintenu `tests/test_dashboard_http.py` lance le serveur standard sur `127.0.0.1` avec un port éphémère et le ferme après les requêtes. La commande utilisateur équivalente pour un accès manuel est :

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Requêtes locales réussies :

| Ressources | Résultat |
| --- | --- |
| `/frontend/` | HTTP 200, titre MedTrace présent |
| CSS et les six modules JS | HTTP 200, types CSS/JavaScript corrects |
| Trois fixtures JSON | HTTP 200, type JSON |
| ECG et rapport de démonstration | HTTP 200 |
| Fixture partagée samples/csv_contract_cases.json | HTTP 200 |

**14 ressources HTTP au total**, incluant les six modules JS, dont `waveform.js`. Le serveur a été arrêté après cette vérification. Le README donne la commande pour le relancer. Cette vérification confirme le démarrage et la disponibilité des ressources ; elle ne constitue pas une vérification visuelle du rendu.

## Limite de vérification visuelle

L’inventaire de contrôle UI a de nouveau renvoyé **aucun navigateur et aucune application disponibles** pendant cette passe corrective. Il n’a donc pas été possible d’exécuter un parcours visuel, de vérifier les dimensions réelles ou de produire des captures d’écran authentiques dans cette session.

Les contrôles statiques et les tests JS ont été exécutés, mais ne remplacent pas cette vérification visuelle. Le parcours manuel complet, y compris clavier, mobile, erreurs, historique et modification simulée, est dans `tests/test_ui_manual.md`. Aucune capture artificielle n’est fournie.

Restent précisément à tester dans un navigateur : sélection native des fichiers/DataTransfer, rendu du signal normal et extrême, messages et compteurs 8/8 ou INCOMPLET, scénario complet d’upload/erreurs/historique/verify, disposition desktop et 390 px, clavier/focus/annonces, rechargement de session, connexion API et CORS. Conserver les captures authentiques prévues par le plan manuel.

## Intégration restante chez les collègues

Le backend de Mrabet et le registre d’Abidi n’étaient pas présents. Il reste à convenir du JSON d’historique, de la lignée causale proposée et des conventions de vérification détaillées dans `docs/contracts.md`, imposer les contrôles de complétude côté backend, autoriser CORS ou servir le frontend depuis FastAPI, puis exécuter les quatre routes avec leurs vrais modules. La détection réelle d’une modification hors chaîne et les transactions Fabric doivent être démontrées dans la branche intégrée. Une interface API connectée peut retourner ledger_mode=MOCK ; transport réel et registre réel sont deux notions distinctes.
