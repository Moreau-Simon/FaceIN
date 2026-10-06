# Partie réseau — Noeuds de vérification décentralisés

## Lancer le squelette

Depuis la racine du projet :

```bash
docker-compose up --build
```

Vous devriez voir les trois noeuds (`node-a`, `node-b`, `node-c`) démarrer
et logguer leur identité + la liste de leurs pairs, toutes les 5 secondes.

C'est volontairement minimal : l'objectif de cette première étape est de
valider que l'architecture "un seul code, plusieurs instances via
variables d'environnement" fonctionne, avant d'ajouter la vraie logique
métier.

## Prochaines étapes, dans l'ordre

1. **Générer le code gRPC** à partir des `.proto` partagés :
   ```bash
   python -m grpc_tools.protoc \
     -I shared/proto \
     --python_out=node \
     --grpc_python_out=node \
     shared/proto/verification.proto shared/proto/sync.proto shared/proto/revocation.proto
   ```

2. **Implémenter `grpc/server.py`** : faire répondre chaque noeud sur son port,
   avec des réponses mockées pour `VerifierPreuve` (toujours `accepte=True`
   par exemple) — ça permet au dev de commencer à tester ses appels client
   sans attendre que tout soit fini.

3. **Implémenter `grpc/peer_client.py`** : faire qu'un noeud puisse appeler
   un autre noeud (test simple : `node-a` ping `node-b` au démarrage).

4. **Brancher `consensus/validation.py`** une fois que plusieurs noeuds
   répondent, pour calculer une vraie majorité.

5. **Implémenter `merkle/tree.py` et `merkle/sync.py`** avec des données
   de test factices, en attendant le schéma final de la BDD.

## Config partagée

Le fichier `shared/config/noeuds.yaml` sert de référence humaine pour la
liste des noeuds et les paramètres de consensus/sync — la configuration
réellement utilisée par chaque conteneur passe par les variables
d'environnement du `docker-compose.yml`, pour rester cohérent avec le
principe "un seul code, configuré au démarrage".
