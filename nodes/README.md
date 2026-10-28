# Partie réseau — Noeuds de vérification décentralisés

## Lancer le squelette

Depuis la racine du projet :

```bash
docker-compose up --build
```

Vous devriez voir les trois noeuds (`node-a`, `node-b`, `node-c`) démarrer
et logguer leur identité et la liste de leurs pairs. Une fois le serveur gRPC
démarré, chaque noeud envoie un heartbeat à chacun de ses pairs en parallèle,
puis attend l'intervalle configuré avant le cycle suivant. Les changements
d'état sont journalisés sans répéter les mêmes messages à chaque tour.
L'intervalle et le délai maximal d'un appel heartbeat sont configurés dans
`shared/config/noeuds.yaml`, sous `heartbeat`. Chaque cycle attend le pair le
plus lent, dans la limite du délai de chaque appel.
`docker-compose.yml` accorde 10 secondes à chaque nœud pour s'arrêter après
`docker stop`. Ce délai est supérieur au timeout heartbeat configuré (3 s),
avec une marge pour terminer les appels en cours et fermer le serveur.

C'est volontairement minimal : l'objectif de cette première étape est de
valider que l'architecture "un seul code, plusieurs instances via
variables d'environnement" fonctionne, avant d'ajouter la vraie logique
métier.

## État de la vérification

Le parcours gRPC nonce → preuve → consensus → token est implémenté pour la
démonstration, mais **ce n'est pas encore une authentification réelle** :

- Le vérificateur de preuve est un mock dans
  `node/consensus/validation.py`, fonction `valider_avec_mock`. Il accepte
  toute preuve non vide. Remplacez cette fonction par l'intégration du
  vérificateur ZKP lorsqu'il sera disponible. Elle reçoit l'identifiant
  utilisateur, la preuve binaire, le nonce et le service cible. Cette
  fonction est utilisée localement et par `ConsensusService`.
- L'accès aux données d'aide de l'utilisateur n'est pas branché. La méthode
  `RecupererDonneeAide` de `node/network/server.py` renvoie actuellement
  `trouve=False`. Remplacez ce stub par l'accès à la BDD et définissez avec
  l'équipe le format des données et paramètres retournés.
- Les nonces sont conservés en mémoire par `node/verification/nonces.py`.
  Cette solution suffit à la démo, mais les nonces sont perdus au redémarrage
  et ne sont pas partagés entre processus. Remplacez le stockage par une
  solution persistante/partagée si le déploiement l'exige.
- La fabrique de token est injectée dans `node/main.py` et produit
  actuellement un token aléatoire non signé. Définissez et implémentez le
  format, la signature, l'expiration et la validation avant tout usage réel.

Le démarrage du serveur et l'injection des dépendances sont assemblés dans
`node/main.py`; les RPC et leurs contrats sont dans
`shared/proto/verification.proto` et `shared/proto/consensus.proto`.
Les tests utilisent un mock et des serveurs gRPC locaux : ils vérifient le
comportement du prototype, pas la cryptographie ZKP ni l'accès à la BDD.

## Tester le parcours

Depuis la racine du dépôt, générez d'abord les stubs gRPC pour l'exécution
locale, si nécessaire :

```bash
python -m grpc_tools.protoc -I nodes/shared/proto --python_out=nodes/node --grpc_python_out=nodes/node nodes/shared/proto/verification.proto nodes/shared/proto/sync.proto nodes/shared/proto/revocation.proto nodes/shared/proto/consensus.proto
```

Puis lancez la suite de tests :

```bash
python -m pytest nodes/node/tests
```

`test_nonces.py` couvre l'usage unique, l'expiration, le mauvais propriétaire,
les nonces inconnus et les consommations concurrentes. Les tests de
`test_verification_service.py` couvrent les refus et acceptations. Le test
`test_verification_integration.py` lance trois serveurs gRPC sur des ports
libres et vérifie que le parcours atteint le quorum de deux nœuds lorsque le
troisième est arrêté.

## Client manuel avec Docker Compose

Après `docker compose up --build`, lancez depuis la racine :

```bash
docker compose exec node-a python client_verification.py --utilisateur-id demo --preuve preuve-de-test
```

`--preuve preuve-de-test` est uniquement une valeur fictive : le mock actuel
l'accepte parce qu'elle n'est pas vide. N'utilisez pas ce client, le mock ou
le token actuel pour protéger un service réel. Pour joindre un autre nœud ou
utiliser d'autres valeurs, fournissez `--address`, `--utilisateur-id`,
`--preuve` et éventuellement `--service-cible`.

## Config partagée

Le `docker-compose.yml` est la source de vérité pour la topologie des noeuds
et leurs pairs (`NODE_ID`, `NODE_PORT`, `PEERS`). Le fichier
`shared/config/noeuds.yaml` contient les paramètres partagés de consensus,
de synchronisation Merkle et de heartbeat, chargés et validés au démarrage
par `node/config.py`.

Les `NODE_ID` sont considérés comme stables pendant l'exécution. Le registre
associe l'identité annoncée à l'adresse du pair et refuse qu'elle change à
chaud. Si un `NODE_ID` doit être modifié, arrêter puis recréer tous les
conteneurs afin que chaque registre en mémoire oublie les anciennes
associations :

```bash
docker compose down
docker compose up --build
```
