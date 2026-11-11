# Vérification fonctionnelle du dashboard

Servir la racine avec `python -m http.server 5500 --bind 127.0.0.1`, puis ouvrir `http://127.0.0.1:5500/frontend/`. Aucun backend n’est nécessaire au parcours MOCK. Tous les fichiers doivent être synthétiques. Les vérifications ci-dessous constituent un plan à exécuter dans un navigateur ; leur présence ne signifie pas qu’elles ont été exécutées automatiquement.

| Étape | Action | Résultat attendu |
| --- | --- | --- |
| 1 | Ouvrir la page | Prototype non diagnostic et mode MOCK visibles ; pas de fausse analyse initiale |
| 2 | Analyser sans fichier | Message français demandant les deux fichiers ; bouton réactivé ; aucun dossier |
| 3 | Charger les fichiers de démonstration | Deux noms de fichiers visibles, aperçu du signal synthétique ; aucun appel d’analyse automatique |
| 4 | Analyser, scénario confiance élevée | UUID du dossier ; `demo_class_A`, 91 %, `ACCEPTED`, explication MOCK, motif de cohérence non évaluée |
| 5 | Consulter les preuves | Huit lignes, hashes complets, parent racine puis liens, `storage_ref`, `MOCK-…`, mode MOCK visible |
| 6 | Vérifier l’intégrité | Badge global `VALID`, huit lignes `VALID`, nouvel événement simulé |
| 7 | Simuler une modification | Indication de simulation, badge à revérifier ; aucune modification disque revendiquée |
| 8 | Revérifier | `MODIFIED` global et sur processed ; hashes attendu/actuel distincts ; validation initiale historique conservée |
| 9 | Analyser en confiance faible | Nouveau UUID, 62 %, `REVIEW_REQUIRED`, motif du seuil 75 % |
| 10 | Analyser en mauvaise qualité | `REVIEW_REQUIRED`, motif de qualité ; aucune qualité clinique déduite du fichier |
| 11 | Analyser en artefact manquant | `REJECTED`, motif d’artefact ; vérification `MISSING` |
| 12 | Analyser en intégrité compromise | `REJECTED` ; vérification `MODIFIED` |
| 13 | Ouvrir un dossier antérieur | Résultat et aperçu correspondants, historique récupéré via l’adaptateur ; aucun mélange de dossiers |
| 14 | Importer ecg_invalid.csv ou report_invalid.txt | Erreur lisible ; aucun nouveau dossier, indication si le résultat précédent reste affiché |
| 15 | Importer fichier vide, mauvais suffixe ou trop gros | Erreur lisible et bouton disponible après échec |
| 16 | Cliquer rapidement deux fois Analyser | Un seul dossier ; contrôles désactivés pendant le traitement |
| 17 | Actualiser l’historique | Journal rafraîchi, résultat de validation conservé |
| 18 | Recharger la page | Session effacée ; aucun fichier ni dossier persistant dans le navigateur |
| 19 | Choisir API avec service absent, analyser | Message réseau/CORS ; aucun dossier MOCK ni fallback silencieux |
| 20 | URL API invalide (file:, identifiants, etc.) | Erreur explicite ; ancien adaptateur conservé |
| 21 | Naviguer au clavier | Fichiers, scénario, analyse, preuves, historique accessibles ; focus visible ; erreurs annoncées |
| 22 | Ouvrir à 390 px de large | Sections empilées ; seule la table de preuves défile horizontalement |
| 23 | Importer un ECG `signal` avec `-1e308` puis `1e308`, lancer l’analyse MOCK | Deux points et tracé visible ; aucun NaN/Infinity dans l’attribut SVG `points` ; dashboard utilisable |
| 24 | Importer un CSV avec ligne vide avant l’en-tête | Rejet avant l’appel d’analyse, comme Python ; lignes totalement vides après l’en-tête acceptées |
| 25 | Importer un CSV avec champ supplémentaire de 131 072 puis 131 073 caractères | Borne exacte acceptée ; dépassement rejeté, y compris dans un champ cité ou Unicode |
| 26 | Faire retourner par un stub une analyse ACCEPTED/REVIEW_REQUIRED avec zéro ou sept artefacts | Erreur de contrat explicite ; aucun nouveau dossier complet affiché ; ancien résultat identifié comme précédent |
| 27 | Faire retourner un UUID/type dupliqué, un cycle, un parent absent ou un parent de type ultérieur | Réponse refusée avant rendu du résultat ; bouton réactivé |
| 28 | Faire retourner un REJECTED avec deux artefacts source puis aucun artefact | Statut REJECTED et compteur INCOMPLET n/8 ; aucun artefact inventé ; vérification désactivée pour zéro |
| 29 | Faire retourner les huit types dans un ordre différent, avec deux racines brutes | Réponse acceptée si la lignée respecte la politique causale documentée ; huit métadonnées, intégrité encore séparée |

## Après intégration des modules des collègues

1. Démarrer FastAPI de Mrabet, autoriser l’origine du frontend et passer en mode API. Importer les fichiers valides ; vérifier que les quatre routes exactes apparaissent dans le journal réseau.
2. Vérifier avec Mrabet que `check_inputs` est réellement exécuté côté serveur et que `report_clean` est utilisé comme contexte. Contourner les contrôles navigateur par un client HTTP pour confirmer les HTTP 422 du serveur.
3. Envoyer `ecg_short.csv` : format accepté par notre contrôle, qualité insuffisante détectée par son prétraitement. Ne pas confondre scénario MOCK et prétraitement réel.
4. Appeler `/verify` sur les fichiers réels. Modifier un artefact de démonstration dans `data/cases/<case_id>/` puis revérifier : au moins `MODIFIED`. Le bouton MOCK ne sert pas à cette expérience.
5. Arrêter le registre : le backend doit signaler `UNVERIFIABLE` et ne pas présenter une preuve verte. Une vérification partielle ou des hashes contradictoires doivent être refusés par le frontend.
6. En FABRIC, demander à Abidi de fournir les vraies preuves de transaction. Ne pas remplacer les identifiants MOCK pour fabriquer une démonstration Fabric.
7. Confirmer avec Mrabet la politique de lignée et imposer la complétude côté serveur. Le contrôle frontend de métadonnées n’est pas une preuve de présence réelle des fichiers ou d’intégrité.
8. Confirmer ensemble les propositions d’historique, de hashes null et de priorité des résultats `/verify` ; renvoyer une vérification pour chaque artefact attendu.

## Captures réelles à conserver

Enregistrer dans `docs/captures/` : `01-upload.png`, `02-resultat.png`, `03-historique.png`, `04-modification-mock.png` et éventuellement `05-modification-api.png` après intégration. Le mode MOCK doit rester visible sur les captures simulées. Une capture n’est une preuve Fabric que si le service réel a effectivement été interrogé.

Aucune capture n’a été fabriquée par code. Consulter `docs/verification.md` pour savoir quelles vérifications ont réellement pu être exécutées dans cet environnement.
