"""
Logique de consensus léger entre noeuds.

Principe : une authentification n'est validée que si le seuil de majorité
(voir noeuds.yaml -> consensus.seuil_majorite) de noeuds interrogés confirment
la preuve, dans le délai imparti (timeout_ms).

A implémenter :
    - interroger les pairs en parallèle (asyncio ou threads)
    - collecter les réponses avant expiration du timeout
    - exclure un pair qui ne répond pas à temps du calcul de majorité
    - retourner accepté/refusé selon le seuil atteint ou non

Pour commencer à développer SANS attendre le vrai vérificateur ZKP du dev,
mocker la fonction de vérification avec une valeur fixe (True/False) ici.
"""


def valider_avec_mock(preuve_recue: str) -> bool:
    """Mock temporaire - à remplacer par un vrai appel au vérificateur ZKP."""
    return bool(preuve_recue)
