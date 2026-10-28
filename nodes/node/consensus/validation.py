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
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError,
    as_completed,
)

def valider_avec_mock(
    utilisateur_id: str,
    preuve_recue: bytes,
    nonce: str,
    service_cible: str,
) -> bool:
    """Mock temporaire - à remplacer par un vrai appel au vérificateur ZKP."""
    return bool(preuve_recue)


def decider(demande, pairs, verifier_local, interroger_pair, seuil, timeout_s):
    """Retourne True si le seuil de votes POUR (initiateur inclus) est atteint.

    ``interroger_pair`` peut retourner un booléen ou le tuple
    ``(node_id, vote)`` renvoyé par le client gRPC.
    """
    pour = (
        1
        if verifier_local(
            demande.utilisateur_id,
            demande.preuve_zkp,
            demande.nonce,
            demande.service_cible,
        )
        else 0
    )
    if pour >= seuil:
        return True

    pool = ThreadPoolExecutor(max_workers=max(1, len(pairs)))
    futures = [pool.submit(interroger_pair, p, demande, timeout_s) for p in pairs]
    try:
        for futur in as_completed(futures, timeout=timeout_s):
            try:
                resultat = futur.result()
                vote = resultat[1] if isinstance(resultat, tuple) else resultat
                if vote is True:
                    pour += 1
            except Exception:
                continue
            if pour >= seuil:
                return True
    except TimeoutError:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return False