"""Tests unitaires du service RPC de vérification."""

import verification_pb2

from network.server import VerificationService
from verification.nonces import NonceStore


def _demande(utilisateur_id, nonce, preuve=b"preuve-valide"):
    return verification_pb2.DemandeVerification(
        utilisateur_id=utilisateur_id,
        preuve_zkp=preuve,
        nonce=nonce,
        timestamp=123,
        service_cible="service-1",
    )


def test_verifier_preuve_refuse_un_nonce_invalide_sans_appeler_le_decideur():
    appels_decideur = []
    service = VerificationService(
        "node-a",
        NonceStore(),
        lambda demande: appels_decideur.append(demande) or True,
        lambda utilisateur_id: "token-test",
    )

    reponse = service.VerifierPreuve(
        _demande("user-1", "nonce-inconnu"),
        context=None,
    )

    assert reponse.accepte is False
    assert reponse.raison_refus == "nonce invalide ou expiré"
    assert reponse.token == ""
    assert appels_decideur == []


def test_verifier_preuve_refuse_si_le_consensus_n_est_pas_atteint():
    nonces = NonceStore()
    nonce, _ = nonces.emettre("user-1")
    appels_token = []
    service = VerificationService(
        "node-a",
        nonces,
        lambda demande: False,
        lambda utilisateur_id: appels_token.append(utilisateur_id),
    )

    reponse = service.VerifierPreuve(
        _demande("user-1", nonce),
        context=None,
    )

    assert reponse.accepte is False
    assert reponse.raison_refus == "consensus non atteint"
    assert reponse.token == ""
    assert reponse.score_anomalie == 0
    assert appels_token == []


def test_verifier_preuve_accepte_et_retourne_un_token():
    nonces = NonceStore()
    nonce, _ = nonces.emettre("user-1")
    demande_consensus = []
    service = VerificationService(
        "node-a",
        nonces,
        lambda demande: demande_consensus.append(demande) or True,
        lambda utilisateur_id: f"token-{utilisateur_id}",
    )

    reponse = service.VerifierPreuve(
        _demande("user-1", nonce),
        context=None,
    )

    assert reponse.accepte is True
    assert reponse.raison_refus == ""
    assert reponse.token == "token-user-1"
    assert reponse.score_anomalie == 0
    assert len(demande_consensus) == 1
    assert demande_consensus[0].utilisateur_id == "user-1"
    assert demande_consensus[0].preuve_zkp == b"preuve-valide"
    assert demande_consensus[0].nonce == nonce
    assert demande_consensus[0].service_cible == "service-1"


def test_nonce_est_consomme_meme_si_le_consensus_refuse():
    nonces = NonceStore()
    nonce, _ = nonces.emettre("user-1")
    service = VerificationService(
        "node-a",
        nonces,
        lambda demande: False,
        lambda utilisateur_id: "token-test",
    )
    demande = _demande("user-1", nonce)

    premier_resultat = service.VerifierPreuve(demande, context=None)
    second_resultat = service.VerifierPreuve(demande, context=None)

    assert premier_resultat.raison_refus == "consensus non atteint"
    assert second_resultat.raison_refus == "nonce invalide ou expiré"
