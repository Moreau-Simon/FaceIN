# Partie réseau — Noeuds de vérification décentralisés

## Lancer le squelette

Depuis la racine du projet :

```bash
docker-compose up --build
```

Vous devriez voir les trois noeuds (`node-a`, `node-b`, `node-c`) démarrer
et logguer leur identité et la liste de leurs pairs. Une fois le serveur gRPC
démarré, chaque noeud envoie un heartbeat à chacun de ses pairs, puis attend
5 secondes avant le cycle suivant. Les envois, réponses et erreurs sont
journalisés ; chaque appel expire après 3 secondes au maximum.

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

Le fichier `shared/config/noeuds.yaml` sert de référence humaine pour la
liste des noeuds et les paramètres de consensus/sync — la configuration
réellement utilisée par chaque conteneur passe par les variables
d'environnement du `docker-compose.yml`, pour rester cohérent avec le
principe "un seul code, configuré au démarrage".
