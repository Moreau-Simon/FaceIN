"""
Tests des défis de vie liés à la session (chantier 11, architecture B).

Couvre : défi invalide, expiré, réutilisé, mauvais utilisateur, autre session,
mauvais ordre, client sans module de liveness, contournement simulé côté frontend
(limite documentée), jeton altéré, plausibilité temporelle, dérivation déterministe
et configuration du secret.
"""

import os
import sys
import time
import unittest
from collections import Counter
from unittest.mock import patch

os.environ.setdefault("STORE_BACKEND", "memory")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from models import AuthenticateRequest, LivenessReport  # noqa: E402
from services import challenge_secret, liveness, rate_limiter, store  # noqa: E402

SECRET_TEST = "secret-de-test-des-challenges-facein-0123456789"
NONCE_1 = "1111111111111111111111111111111122222222222222222222222222222222"
NONCE_2 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def rapport_conforme(user_id, nonce, expires_at=None, defis=None, jeton=None, debut=1_700_000_000_000):
    """Rapport tel que le produirait le frontend après exécution des défis."""
    expires_at = int(time.time()) + 60 if expires_at is None else expires_at
    attendus, jeton_serveur = liveness.preparer_defis(user_id, nonce, expires_at)
    executes = []
    for i, cle in enumerate(defis if defis is not None else attendus):
        executes.append({"type": cle, "debut_ms": debut + i * 2500, "fin_ms": debut + i * 2500 + 1200})
    return LivenessReport(expires_at=expires_at, jeton=jeton or jeton_serveur, defis=executes)


class BaseLiveness(unittest.TestCase):
    def setUp(self):
        self._env = patch.dict(os.environ, {"FACEIN_CHALLENGE_SECRET": SECRET_TEST})
        self._env.start()

    def tearDown(self):
        self._env.stop()


class TestDerivationDefis(BaseLiveness):
    def test_derivation_deterministe_distincte_et_autorisee(self):
        a = liveness.deriver_defis("alice", NONCE_1)
        self.assertEqual(a, liveness.deriver_defis("alice", NONCE_1))
        self.assertEqual(len(a), liveness.NOMBRE_DEFIS)
        self.assertEqual(len(set(a)), len(a))
        self.assertTrue(set(a) <= set(liveness.DEFIS_DISPONIBLES))

    def test_derivation_insensible_a_la_casse_du_nonce(self):
        self.assertEqual(
            liveness.deriver_defis("alice", NONCE_2),
            liveness.deriver_defis("alice", NONCE_2.upper()),
        )

    def test_derivation_depend_du_secret(self):
        """Sans le secret serveur, un attaquant ne peut pas prédire les défis."""
        tirages_a = [tuple(liveness.deriver_defis("alice", f"{i:064x}")) for i in range(40)]
        with patch.dict(os.environ, {"FACEIN_CHALLENGE_SECRET": SECRET_TEST + "-autre"}):
            tirages_b = [tuple(liveness.deriver_defis("alice", f"{i:064x}")) for i in range(40)]
        self.assertNotEqual(tirages_a, tirages_b)

    def test_repartition_des_tirages_sans_biais_grossier(self):
        compteur = Counter()
        for i in range(2400):
            compteur.update(liveness.deriver_defis("u", f"{i:064x}"))
        attendu = 2400 * liveness.NOMBRE_DEFIS / len(liveness.DEFIS_DISPONIBLES)
        for cle in liveness.DEFIS_DISPONIBLES:
            self.assertLess(abs(compteur[cle] - attendu), attendu * 0.15, compteur)


class TestVerificationRapport(BaseLiveness):
    def test_rapport_conforme_accepte(self):
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport_conforme("alice", NONCE_1))
        self.assertTrue(ok, raison)

    def test_client_sans_module_de_liveness_refuse(self):
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, None)
        self.assertFalse(ok)
        self.assertIn("absent", raison)

    def test_defi_invalide_refuse(self):
        attendus = liveness.deriver_defis("alice", NONCE_1)
        autre = next(d for d in liveness.DEFIS_DISPONIBLES if d not in attendus)
        rapport = rapport_conforme("alice", NONCE_1, defis=[attendus[0], autre])
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("non conformes", raison)

    def test_defi_inconnu_refuse(self):
        attendus = liveness.deriver_defis("alice", NONCE_1)
        rapport = rapport_conforme("alice", NONCE_1, defis=[attendus[0], "danse"])
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])

    def test_defi_manquant_refuse(self):
        attendus = liveness.deriver_defis("alice", NONCE_1)
        rapport = rapport_conforme("alice", NONCE_1, defis=attendus[:1])
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])

    def test_defi_en_double_refuse(self):
        attendus = liveness.deriver_defis("alice", NONCE_1)
        rapport = rapport_conforme("alice", NONCE_1, defis=attendus + [attendus[0]])
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])

    def test_defis_dans_le_mauvais_ordre_refuses(self):
        attendus = liveness.deriver_defis("alice", NONCE_1)
        rapport = rapport_conforme("alice", NONCE_1, defis=list(reversed(attendus)))
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("mauvais ordre", raison)

    def test_defi_expire_refuse(self):
        expires_at = int(time.time()) - 1
        rapport = rapport_conforme("alice", NONCE_1, expires_at=expires_at)
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("expirés", raison)

    def test_prolongation_de_l_expiration_refusee(self):
        """Le client ne peut pas repousser l'expiration : elle est couverte par le jeton."""
        rapport = rapport_conforme("alice", NONCE_1, expires_at=int(time.time()) - 5)
        rapport.expires_at = int(time.time()) + 3600
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("non associés", raison)

    def test_defi_associe_au_mauvais_utilisateur_refuse(self):
        rapport = rapport_conforme("alice", NONCE_1)
        ok, raison = liveness.verifier_rapport("mallory", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("non associés", raison)

    def test_defi_associe_a_une_autre_session_refuse(self):
        rapport = rapport_conforme("alice", NONCE_1)
        ok, _ = liveness.verifier_rapport("alice", NONCE_2, rapport)
        self.assertFalse(ok)

    def test_defi_reutilise_sur_une_nouvelle_session_refuse(self):
        """Un rapport valide de la session 1 rejoué avec le nonce de la session 2."""
        ancien = rapport_conforme("alice", NONCE_1)
        self.assertTrue(liveness.verifier_rapport("alice", NONCE_1, ancien)[0])
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_2, ancien)[0])

    def test_defi_associe_a_un_autre_service_refuse(self):
        rapport = rapport_conforme("alice", NONCE_1)
        ok, _ = liveness.verifier_rapport("alice", NONCE_1, rapport, service="autre-service")
        self.assertFalse(ok)

    def test_jeton_altere_refuse(self):
        rapport = rapport_conforme("alice", NONCE_1)
        rapport.jeton = ("0" if rapport.jeton[0] != "0" else "1") + rapport.jeton[1:]
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])

    def test_duree_non_plausible_refusee(self):
        rapport = rapport_conforme("alice", NONCE_1)
        rapport.defis[0].fin_ms = rapport.defis[0].debut_ms + 10  # 10 ms : impossible
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])
        rapport = rapport_conforme("alice", NONCE_1)
        rapport.defis[0].fin_ms = rapport.defis[0].debut_ms + liveness.DUREE_MAX_DEFI_MS + 1
        self.assertFalse(liveness.verifier_rapport("alice", NONCE_1, rapport)[0])

    def test_chronologie_incoherente_refusee(self):
        rapport = rapport_conforme("alice", NONCE_1)
        rapport.defis[1].debut_ms = rapport.defis[0].debut_ms  # chevauchement
        rapport.defis[1].fin_ms = rapport.defis[1].debut_ms + 1000
        ok, raison = liveness.verifier_rapport("alice", NONCE_1, rapport)
        self.assertFalse(ok)
        self.assertIn("Chronologie", raison)

    def test_contournement_simule_cote_frontend_limite_documentee(self):
        """
        LIMITE CONNUE : un client modifié qui n'exécute aucun défi mais recopie la
        réponse de /api/nonce produit un rapport accepté. Le contrôle B garantit
        l'association à la session, pas l'exécution réelle devant la caméra.
        La garantie serveur repose sur la passkey (voir test_webauthn.py).
        """
        expires_at = int(time.time()) + 60
        defis, jeton = liveness.preparer_defis("alice", NONCE_1, expires_at)  # = réponse /nonce
        forge = LivenessReport(
            expires_at=expires_at,
            jeton=jeton,
            defis=[
                {"type": d, "debut_ms": 1000 * i * 3, "fin_ms": 1000 * i * 3 + 500}
                for i, d in enumerate(defis)
            ],
        )
        self.assertTrue(liveness.verifier_rapport("alice", NONCE_1, forge)[0])


class TestSecretChallenges(unittest.TestCase):
    def test_secret_obligatoire_en_production(self):
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "FACEIN_CHALLENGE_SECRET": ""}):
            with self.assertRaises(RuntimeError):
                challenge_secret.verifier_configuration_secret()

    def test_secret_trop_court_refuse(self):
        with patch.dict(os.environ, {"FACEIN_CHALLENGE_SECRET": "court"}):
            with self.assertRaises(RuntimeError):
                challenge_secret.verifier_configuration_secret()

    def test_secret_aleatoire_par_processus_hors_production(self):
        with patch.dict(os.environ, {"FACEIN_ENV": "development", "FACEIN_CHALLENGE_SECRET": ""}):
            premier = challenge_secret.charger_secret()
            self.assertEqual(premier, challenge_secret.charger_secret())
            self.assertGreaterEqual(len(premier), 32)

    def test_meme_secret_meme_defis_sur_plusieurs_instances(self):
        """Deux instances de l'API partageant le secret calculent les mêmes défis."""
        with patch.dict(os.environ, {"FACEIN_CHALLENGE_SECRET": SECRET_TEST}):
            a = liveness.preparer_defis("alice", NONCE_1, 1234)
            challenge_secret._secret_processus = None  # simule un autre processus
            b = liveness.preparer_defis("alice", NONCE_1, 1234)
        self.assertEqual(a, b)


class TestRoutesLiveness(BaseLiveness):
    def setUp(self):
        super().setUp()
        store.reset_store()
        rate_limiter.reset_rate_limiter()

    def tearDown(self):
        store.reset_store()
        super().tearDown()

    def test_route_nonce_renvoie_defis_derives_et_jeton(self):
        from routes.nonce import get_nonce

        exp = int(time.time()) + 60
        with patch("routes.nonce.request_nonce_from_node", return_value=(NONCE_1, exp)):
            res = get_nonce("alice")
        self.assertEqual(res.defis, liveness.deriver_defis("alice", NONCE_1))
        self.assertEqual(res.defis_jeton, liveness.calculer_jeton("alice", NONCE_1, exp, res.defis))
        self.assertEqual(res.webauthn["userVerification"], "required")
        self.assertNotIn("allowCredentials", res.webauthn)

    def test_authentification_sans_rapport_refusee_avant_zkp_et_consensus(self):
        from routes import authenticate as route

        store.save_commitment("alice", "123456789")
        hi, lo = str(int(NONCE_1, 16) >> 128), str(int(NONCE_1, 16) & ((1 << 128) - 1))
        req = AuthenticateRequest(
            user_id="alice",
            proof={"pi_a": ["1", "2"], "pi_b": [["1", "2"], ["3", "4"]], "pi_c": ["1", "2"]},
            public_signals=["123456789", "16000000", hi, lo],
            nonce=NONCE_1,
        )
        with patch.object(route, "verify_proof") as verify, patch.object(route, "verify_on_nodes") as nodes:
            res = route.authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertIn("liveness", res.raison_refus)
        verify.assert_not_called()
        nodes.assert_not_called()

    def test_authentification_rapport_d_une_autre_session_refusee(self):
        from routes import authenticate as route

        store.save_commitment("alice", "123456789")
        hi, lo = str(int(NONCE_2, 16) >> 128), str(int(NONCE_2, 16) & ((1 << 128) - 1))
        req = AuthenticateRequest(
            user_id="alice",
            proof={"pi_a": ["1", "2"], "pi_b": [["1", "2"], ["3", "4"]], "pi_c": ["1", "2"]},
            public_signals=["123456789", "16000000", hi, lo],
            nonce=NONCE_2,
            liveness=rapport_conforme("alice", NONCE_1).model_dump(),
        )
        with patch.object(route, "verify_on_nodes") as nodes:
            res = route.authenticate(req)
        self.assertFalse(res.authenticated)
        nodes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
