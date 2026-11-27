# Suite de tests Backend FaceIN

## Commande globale

Depuis la racine du dépôt :

```bash
pip install -r api/requirements.txt -r nodes/node/requirements-dev.txt
python scripts/run_backend_tests.py            # toutes les suites disponibles
python scripts/run_backend_tests.py --strict   # une suite non exécutable = échec
```

Le lanceur compile les fichiers `.proto` (fichiers `*_pb2*.py` ignorés par Git), puis exécute chaque
suite dans un processus séparé et termine par un bilan :

```
BILAN DES TESTS BACKEND FACEIN
  RÉUSSI       API Gateway (api/tests)
  ÉCHOUÉ       Nœuds (nodes/node/tests)
  NON EXÉCUTÉ  PostgreSQL réel  (TEST_POSTGRES_URL non définie)
  ...
```

Le lanceur force `MOCK_ZKP_VERIFICATION=false` et n'active aucune simulation : un test de sécurité ne
peut pas réussir grâce à un mock positif.

## Catégories couvertes

| Catégorie | Fichiers |
|---|---|
| Unitaires (validation API, nonces, stockage, JWT, signaux publics) | `api/tests/test_gateway.py` |
| Anti-mock en production, concurrence | `api/tests/test_security_hardening.py` |
| Cryptographie Groth16 réelle | `api/tests/test_zkp_crypto.py` |
| Défis de vie liés à la session (B) | `api/tests/test_liveness.py` |
| Passkeys WebAuthn (C), authentificateur logiciel réel | `api/tests/test_webauthn.py` |
| PostgreSQL (unitaires + intégration réelle) | `api/tests/test_store_postgres.py` |
| Consensus, réseau, Merkle, révocation, configuration | `nodes/node/tests/` |

### Garanties anti-mock

- Les votes de consensus ne sont jamais simulés : sans nœud joignable, `verify_on_nodes` refuse
  l'authentification (aucun vote ni jeton fabriqué), quelles que soient les variables d'environnement.
- `FACEIN_ENV=production` (posé par `docker-compose.prod.yml` sur l'API et les 3 nœuds) fait refuser le
  démarrage si `MOCK_ZKP_VERIFICATION` est actif ; une preuve présentée en mode simulation y est refusée.

## Tests nécessitant des dépendances particulières

### Cérémonie Groth16 de test (`test_zkp_crypto.py`)

Les preuves sont de vraies preuves Groth16 produites à partir de `circuits/distance.circom`, avec deux
cérémonies de **test** jetables (clés A et B). Les clés du dépôt (`frontend/circuit/`,
`nodes/shared/verification_key.json`) ne sont jamais modifiées.

```bash
(cd circuits && npm ci)                        # snarkjs + circomlibjs
bash scripts/generate_test_zkp_artifacts.sh    # nécessite circom 2.x dans le PATH (~2 min)
FACEIN_REQUIRE_REAL_ZKP=1 python -m pytest api/tests/test_zkp_crypto.py -v
```

Artefacts produits dans `circuits/build/test-zkp/` (ignoré par Git). Sans artefacts, les tests réels sont
ignorés en local ; avec `FACEIN_REQUIRE_REAL_ZKP=1` (CI), leur absence est une erreur.

Scénarios : preuve correcte (API et nœud), preuve altérée, composantes mélangées, mauvais commitment,
seuil excessif, ancienne preuve rejouée, nonce réécrit, signaux manquants ou supplémentaires, mauvaise
clé de vérification, ancienne version du circuit (2 signaux), imposteur.

`TestCoherenceClesDuDepot` vérifie que `frontend/circuit/distance.zkey` correspond au circuit courant et
que `nodes/shared/verification_key.json` en est issue. **Ces deux tests échouent tant que les clés du
dépôt n'ont pas été régénérées** (la zkey du frontend date de l'ancien circuit à 2 signaux publics).

> Ces cérémonies à un seul contributeur ne remplacent pas une véritable cérémonie de confiance.

### Défis de vie et passkeys (`test_liveness.py`, `test_webauthn.py`)

Aucune dépendance externe : `test_webauthn.py` utilise un authentificateur FIDO2 **logiciel**
(clé ECDSA P-256 réelle, données CBOR et signatures réelles) vérifié par la bibliothèque `webauthn`.

`test_contournement_simule_cote_frontend_limite_documentee` vérifie volontairement qu'un client
modifié peut forger un rapport de défis accepté : c'est la limite connue de l'architecture B.
`test_compte_avec_passkey_sans_assertion_refuse` montre que ce même client est refusé dès que le
compte possède une passkey (architecture C).

### PostgreSQL réel (`TestStorePostgresIntegration`)

Exécutée uniquement si `TEST_POSTGRES_URL` pointe vers une base de **test** isolée (jamais la
production). Les tests vident les tables (`ALLOW_DESTRUCTIVE_STORE_RESET` activé localement au test).

```bash
psql "$TEST_POSTGRES_URL" -f 01_schema.sql
TEST_POSTGRES_URL=postgresql://facein_test:...@127.0.0.1:5432/facein_test \
  python -m pytest api/tests/test_store_postgres.py -v
```

Scénarios : création, doublon, inscriptions concurrentes du même identifiant, mise à jour d'engagement,
consommations simultanées d'un nonce, mauvais propriétaire, expiration, persistance après redémarrage
du pool.

## CI (GitHub Actions)

| Job | Contenu |
|---|---|
| `tests-noeuds` | `nodes/node/tests` |
| `tests-api` | `api/tests` hors Groth16, `MOCK_ZKP_VERIFICATION=false` |
| `tests-postgres` | conteneur `postgres:16-alpine` éphémère + schéma |
| `tests-zkp-reel` | circom + snarkjs, cérémonie de test, `FACEIN_REQUIRE_REAL_ZKP=1` |
| `circuits` | compilation + `npm test` du circuit |

## Limites connues

- 14 tests de `nodes/node/tests` (`test_server.py`, `test_main.py`, …) échouent depuis le chantier 8 :
  leurs doubles de test ne connaissent pas le paramètre `peers` ni `add_generic_rpc_handlers`.
- Les tests de résilience « arrêt / redémarrage d'un nœud » et « perte gRPC » sont couverts au niveau
  des composants (pairs simulés injoignables), pas sur une stack Docker réelle à trois nœuds.
