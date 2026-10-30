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
Chaque nœud expose aussi le protocole standard `grpc.health.v1`. Le contrôle
Docker appelle ce service en mTLS ; l'API ne démarre qu'après que les trois
nœuds sont déclarés sains par Docker Compose (`service_healthy`).

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

Le client utilise le mTLS configuré dans le conteneur (`TLS_CA_CERT`,
`TLS_CERT` et `TLS_KEY`) et se connecte à `node-a:50051`, nom correspondant
au SAN du certificat. Ne remplacez pas cette adresse par `localhost` : le
certificat du nœud ne couvre pas ce nom.

`--preuve preuve-de-test` est uniquement une valeur fictive : le mock actuel
l'accepte parce qu'elle n'est pas vide. N'utilisez pas ce client, le mock ou
le token actuel pour protéger un service réel. Pour joindre un autre nœud ou
utiliser d'autres valeurs, fournissez `--address`, `--utilisateur-id`,
`--preuve` et éventuellement `--service-cible`.
L'option `--insecure` ne doit être utilisée que pour un test où le serveur a
explicitement désactivé TLS.

## Config partagée

Le `docker-compose.yml` est la source de vérité pour la topologie des noeuds
et leurs pairs (`NODE_ID`, `NODE_PORT`, `PEERS`). Le fichier
`shared/config/noeuds.yaml` contient les paramètres partagés de consensus,
de synchronisation Merkle et de heartbeat, chargés et validés au démarrage
par `node/config.py`.
Les pairs IPv4 et DNS utilisent `hostname:port`; les adresses IPv6 doivent
être entre crochets, par exemple `[2001:db8::2]:50052`.

Les `NODE_ID` sont considérés comme stables pendant l'exécution. Le registre
associe l'identité annoncée à l'adresse du pair et refuse qu'elle change à
chaud. Si un `NODE_ID` doit être modifié, arrêter puis recréer tous les
conteneurs afin que chaque registre en mémoire oublie les anciennes
associations :

```bash
docker compose down
docker compose up --build
```

## Configuration TLS/mTLS des nœuds

FaceIN utilise le mTLS (Mutual Transport Layer Security) pour sécuriser les communications gRPC entre les nœuds du réseau et l'API. Les communications sont chiffrées et chaque composant doit présenter un certificat valide signé par l'autorité de certification (CA) interne.

### 1. Récupérer la CA interne

Pour l'environnement de test, les fichiers de la CA sont partagés sur le Discord du projet, dans les messages épinglés.

Récupérer les fichiers suivants :

ca.crt : certificat public de l'autorité de certification.
ca.key : clé privée utilisée pour signer les certificats.

Placer les fichiers aux emplacements suivants :
```bash
text
FaceIN/
├── ca.key
└── nodes/
    └── infra/
        └── tls/
            └── ca.crt
```

Le fichier ca.key doit être placé à la racine du projet, au même niveau que docker-compose.yml. Le certificat public ca.crt doit être placé dans nodes/infra/tls/ca.crt.

Attention : ca.key permet de signer des certificats reconnus par les composants qui font confiance à cette CA. Cette clé est partagée uniquement pour les besoins de l'environnement de test et ne doit pas être utilisée en production.
### 2. Prérequis

Avant de générer les certificats, vérifier que les éléments suivants sont disponibles :

Windows avec PowerShell.
OpenSSL installé et accessible depuis le terminal.
Les fichiers ca.key et nodes/infra/tls/ca.crt.
Le script creation_certs.ps1 à la racine du projet.

Vérifier qu'OpenSSL fonctionne :

powershell
openssl version

### 3. Générer les certificats

Depuis la racine du projet FaceIN, exécuter :

powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\creation_certs.ps1


Cette modification de la politique d'exécution s'applique uniquement à la session PowerShell courante.

Le script génère les certificats et les clés privées nécessaires aux composants configurés, notamment :

node-a
node-b
node-c
api-gateway

Les certificats doivent être signés par la CA interne et contenir les SAN (Subject Alternative Names) correspondant aux noms DNS utilisés par les services dans Docker.

### 4. Organisation des fichiers

Exemple d'organisation du projet :
```bashtext
FaceIN/
├── ca.key
├── creation_certs.ps1
├── certs/
│   ├── node-a.crt
│   ├── node-a.key
│   ├── node-b.crt
│   ├── node-b.key
│   ├── node-c.crt
│   ├── node-c.key
│   ├── api-gateway.crt
│   └── api-gateway.key
├── nodes/
│   └── infra/
│       └── tls/
│           └── ca.crt
└── docker-compose.yml
```

Les fichiers .crt contiennent les certificats. Les fichiers .key contiennent les clés privées associées.

Chaque conteneur doit disposer de son propre certificat et de sa clé privée, ainsi que du certificat public ca.crt. Les chemins utilisés dans Docker Compose doivent correspondre à ceux configurés dans le code Python.

### 5. Protection des fichiers

Les clés privées et les fichiers intermédiaires ne doivent pas être ajoutés au dépôt Git.

Ajouter les règles suivantes au .gitignore :

```bash
gitignore
/ca.key
/certs/
*.key
*.csr
*.srl
```

Le certificat public ca.crt peut être versionné dans le dépôt.

### 6. Environnement de test et production

La CA actuelle est destinée aux tests du projet. Sa clé privée ayant été partagée sur Discord, toute personne qui l'a récupérée pourrait signer des certificats reconnus par les composants qui lui font confiance.

Pour un environnement de production, il faudra créer une nouvelle CA dont la clé privée sera conservée dans un emplacement sécurisé et ne sera jamais partagée. Les certificats des composants devront alors être régénérés et signés par cette nouvelle CA.