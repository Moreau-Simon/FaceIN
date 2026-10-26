# Partie réseau — Noeuds de vérification décentralisés

## Lancer le squelette

Depuis la racine du projet :

```bash
docker-compose up --build
```

Vous devriez voir les trois noeuds (`node-a`, `node-b`, `node-c`) démarrer
et logguer leur identité et la liste de leurs pairs. Une fois le serveur gRPC
démarré, chaque noeud envoie un heartbeat à chacun de ses pairs, puis attend
l'intervalle configuré avant le cycle suivant. Les envois, réponses et erreurs
sont journalisés. L'intervalle et le délai maximal d'un appel heartbeat sont
configurés dans `shared/config/noeuds.yaml`, sous `heartbeat`. Les appels sont
séquentiels : la durée réelle d'un cycle inclut aussi le temps passé à
contacter les pairs.

C'est volontairement minimal : l'objectif de cette première étape est de
valider que l'architecture "un seul code, plusieurs instances via
variables d'environnement" fonctionne, avant d'ajouter la vraie logique
métier.

## Prochaines étapes, dans l'ordre

1. **Générer le code gRPC** à partir des `.proto` partagés. Le
   `node/Dockerfile` le génère automatiquement pendant la construction de
   l'image. Pour une génération locale depuis le dossier `nodes` :
   ```bash
   python -m grpc_tools.protoc \
     -I shared/proto \
     --python_out=node \
     --grpc_python_out=node \
     shared/proto/verification.proto shared/proto/sync.proto shared/proto/revocation.proto
   ```

2. **Étendre `network/server.py`** avec le service de vérification. Le service
   de synchronisation et son endpoint Heartbeat sont déjà opérationnels ;
   l'endpoint `VerifierPreuve` pourra d'abord renvoyer une réponse mockée
   (`accepte=True`) pour tester les appels client.

3. **Étendre `network/peer_client.py`** pour les autres appels entre noeuds.
   L'envoi périodique de heartbeat est déjà branché au démarrage.

4. **Brancher `consensus/validation.py`** une fois que plusieurs noeuds
   répondent, pour calculer une vraie majorité.

5. **Implémenter `merkle/tree.py` et `merkle/sync.py`** avec des données
   de test factices, en attendant le schéma final de la BDD.

## Config partagée

Le `docker-compose.yml` est la source de vérité pour la topologie des noeuds
et leurs pairs (`NODE_ID`, `NODE_PORT`, `PEERS`). Le fichier
`shared/config/noeuds.yaml` contient les paramètres partagés de consensus,
de synchronisation Merkle et de heartbeat, chargés et validés au démarrage
par `node/config.py`.
