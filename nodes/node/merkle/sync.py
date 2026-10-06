"""
Boucle périodique d'échange des racines de Merkle avec les pairs
(voir noeuds.yaml -> sync_merkle.intervalle_secondes).

A implémenter :
    - toutes les N secondes, appeler EchangerRacine sur chaque pair (sync.proto)
    - si racine différente -> déclencher RecupererBranche pour isoler
      la ou les branches divergentes
    - ne retransférer que les feuilles concernées, jamais toute la base
"""
