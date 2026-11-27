"""
Tests de l'attestation matérielle par passkey WebAuthn (chantier 11, architecture C).

Un authentificateur LOGICIEL est utilisé (clé ECDSA P-256 réelle, données
d'authentificateur CBOR et signatures réelles) : la bibliothèque `webauthn`
vérifie réellement chaque attestation et chaque assertion, sans simulation.
"""

import base64
import hashlib
import json
import os
import secrets
import sys
import time
import unittest
from unittest.mock import patch

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

os.environ.setdefault("STORE_BACKEND", "memory")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from models import AuthenticateRequest, PasskeyOptionsRequest, PasskeyVerifyRequest  # noqa: E402
from routes import authenticate as route_auth  # noqa: E402
from routes import webauthn as route_passkey  # noqa: E402
from services import jwt_manager, liveness, rate_limiter, store, webauthn_service  # noqa: E402

ORIGINE = "http://localhost:3000"
RP_ID = "localhost"
NONCE_1 = "1111111111111111111111111111111122222222222222222222222222222222"
NONCE_2 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ENV_TEST = {
    "FACEIN_CHALLENGE_SECRET": "secret-de-test-des-challenges-facein-0123456789",
    "WEBAUTHN_RP_ID": RP_ID,
    "WEBAUTHN_ORIGINS": ORIGINE,
    "JWT_SECRET_KEY": "cle-jwt-de-test-facein-0123456789abcdef",
    "JWT_ENV": "development",
}


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class AuthentificateurLogiciel:
    """Authentificateur FIDO2 minimal (attestation 'none', ES256)."""

    def __init__(self, rp_id=RP_ID, origine=ORIGINE):
        self.cle = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = secrets.token_bytes(32)
        self.rp_id = rp_id
        self.origine = origine
        self.compteur = 0
        self.user_handle = b""

    def _cle_cose(self) -> bytes:
        nums = self.cle.public_key().public_numbers()
        return cbor2.dumps({1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")})

    def _auth_data(self, flags: int, attested: bytes = b"") -> bytes:
        rp_hash = hashlib.sha256(self.rp_id.encode()).digest()
        return rp_hash + bytes([flags]) + self.compteur.to_bytes(4, "big") + attested

    def creer(self, options: dict, uv: bool = True, origine=None) -> dict:
        self.user_handle = unb64(options["user"]["id"])
        client_data = json.dumps({
            "type": "webauthn.create",
            "challenge": options["challenge"],
            "origin": origine or self.origine,
            "crossOrigin": False,
        }).encode()
        attested = (
            bytes(16)
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + self._cle_cose()
        )
        flags = 0x01 | 0x40 | (0x04 if uv else 0)
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": self._auth_data(flags, attested)})
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "attestationObject": b64(attestation),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
        }

    def signer(self, challenge_b64: str, uv: bool = True, origine=None, incrementer=True, user_handle=None) -> dict:
        if incrementer:
            self.compteur += 1
        client_data = json.dumps({
            "type": "webauthn.get",
            "challenge": challenge_b64,
            "origin": origine or self.origine,
            "crossOrigin": False,
        }).encode()
        auth_data = self._auth_data(0x01 | (0x04 if uv else 0))
        signature = self.cle.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "authenticatorData": b64(auth_data),
                "signature": b64(signature),
                "userHandle": b64(self.user_handle if user_handle is None else user_handle),
            },
            "clientExtensionResults": {},
        }


def signaux(commitment, nonce):
    v = int(nonce, 16)
    return [commitment, "16000000", str(v >> 128), str(v & ((1 << 128) - 1))]


PREUVE = {"pi_a": ["1", "2"], "pi_b": [["1", "2"], ["3", "4"]], "pi_c": ["1", "2"]}


class BaseWebAuthn(unittest.TestCase):
    def setUp(self):
        self._env = patch.dict(os.environ, ENV_TEST)
        self._env.start()
        store.reset_store()
        rate_limiter.reset_rate_limiter()
        store.register_new_commitment("alice", "123456789")
        store.register_new_commitment("bob", "987654321")
        self.jwt_alice = "Bearer " + jwt_manager.generate_token("alice")

    def tearDown(self):
        store.reset_store()
        self._env.stop()

    def enregistrer(self, auth, user="alice", jwt=None, **kwargs):
        opts = route_passkey.passkey_options(PasskeyOptionsRequest(user_id=user), authorization=jwt or self.jwt_alice)
        credential = auth.creer(opts.options, **kwargs)
        return route_passkey.passkey_verify(
            PasskeyVerifyRequest(
                user_id=user, credential=credential, challenge=opts.challenge,
                expires_at=opts.expires_at, jeton=opts.jeton,
            ),
            authorization=jwt or self.jwt_alice,
        )

    def requete(self, user, nonce, assertion=None, commitment="123456789"):
        exp = int(time.time()) + 60
        defis, jeton = liveness.preparer_defis(user, nonce, exp)
        rapport = {
            "expires_at": exp,
            "jeton": jeton,
            "defis": [{"type": d, "debut_ms": 1000 + 3000 * i, "fin_ms": 2000 + 3000 * i} for i, d in enumerate(defis)],
        }
        return AuthenticateRequest(
            user_id=user, proof=PREUVE, public_signals=signaux(commitment, nonce),
            nonce=nonce, liveness=rapport, webauthn=assertion,
        )

    def authentifier(self, req):
        """Preuve ZKP et quorum acceptés explicitement : le test porte sur la passkey."""
        with patch.object(route_auth, "verify_proof", return_value=True), patch.object(
            route_auth, "verify_on_nodes", return_value={"consensus": True, "majority": "3/3", "reason": ""}
        ) as noeuds:
            return route_auth.authenticate(req), noeuds


class TestEnregistrementPasskey(BaseWebAuthn):
    def test_enregistrement_valide(self):
        auth = AuthentificateurLogiciel()
        res = self.enregistrer(auth)
        self.assertTrue(res.success)
        creds = store.get_webauthn_credentials("alice")
        self.assertEqual(len(creds), 1)
        self.assertEqual(creds[0]["credential_id"], b64(auth.credential_id))

    def test_enregistrement_sans_session_faceIN_refuse(self):
        with self.assertRaises(HTTPException) as ctx:
            route_passkey.passkey_options(PasskeyOptionsRequest(user_id="alice"), authorization=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_enregistrement_avec_le_jwt_d_un_autre_utilisateur_refuse(self):
        """Un tiers authentifié ne peut pas associer sa passkey au compte d'autrui."""
        jwt_bob = "Bearer " + jwt_manager.generate_token("bob")
        with self.assertRaises(HTTPException) as ctx:
            self.enregistrer(AuthentificateurLogiciel(), user="alice", jwt=jwt_bob)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(store.get_webauthn_credentials("alice"), [])

    def test_enregistrement_jwt_falsifie_refuse(self):
        with self.assertRaises(HTTPException) as ctx:
            self.enregistrer(AuthentificateurLogiciel(), jwt=self.jwt_alice[:-3] + "abc")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_enregistrement_en_double_refuse(self):
        auth = AuthentificateurLogiciel()
        self.enregistrer(auth)
        with self.assertRaises(HTTPException) as ctx:
            self.enregistrer(auth)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_enregistrement_sans_verification_utilisateur_refuse(self):
        with self.assertRaises(HTTPException) as ctx:
            self.enregistrer(AuthentificateurLogiciel(), uv=False)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_enregistrement_depuis_une_autre_origine_refuse(self):
        with self.assertRaises(HTTPException) as ctx:
            self.enregistrer(AuthentificateurLogiciel(), origine="https://phishing.example")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_enregistrement_challenge_ou_jeton_alteres_refuses(self):
        auth = AuthentificateurLogiciel()
        opts = route_passkey.passkey_options(PasskeyOptionsRequest(user_id="alice"), authorization=self.jwt_alice)
        credential = auth.creer(opts.options)
        for challenge, jeton, exp in (
            (b64(secrets.token_bytes(32)), opts.jeton, opts.expires_at),
            (opts.challenge, "0" * 64, opts.expires_at),
            (opts.challenge, opts.jeton, opts.expires_at + 600),
        ):
            with self.assertRaises(HTTPException) as ctx:
                route_passkey.passkey_verify(
                    PasskeyVerifyRequest(user_id="alice", credential=credential, challenge=challenge,
                                         expires_at=exp, jeton=jeton),
                    authorization=self.jwt_alice,
                )
            self.assertEqual(ctx.exception.status_code, 400)

    def test_enregistrement_expire_refuse(self):
        auth = AuthentificateurLogiciel()
        opts = route_passkey.passkey_options(PasskeyOptionsRequest(user_id="alice"), authorization=self.jwt_alice)
        with self.assertRaises(webauthn_service.ErreurWebAuthn):
            webauthn_service.verifier_enregistrement(
                "alice", auth.creer(opts.options), opts.challenge, opts.expires_at, opts.jeton,
                maintenant=opts.expires_at + 1,
            )


class TestAuthentificationPasskey(BaseWebAuthn):
    def setUp(self):
        super().setUp()
        self.auth = AuthentificateurLogiciel()
        self.enregistrer(self.auth)

    def challenge(self, user="alice", nonce=NONCE_1):
        return webauthn_service.challenge_authentification_b64(user, nonce, liveness.SERVICE_CIBLE)

    def test_assertion_valide_acceptee(self):
        res, noeuds = self.authentifier(self.requete("alice", NONCE_1, self.auth.signer(self.challenge())))
        self.assertTrue(res.authenticated, res.raison_refus)
        noeuds.assert_called_once()
        self.assertEqual(store.get_webauthn_credentials("alice")[0]["sign_count"], 1)

    def test_compte_avec_passkey_sans_assertion_refuse(self):
        """Un client modifié qui forge le rapport de défis mais n'a pas la passkey est refusé."""
        res, noeuds = self.authentifier(self.requete("alice", NONCE_1, assertion=None))
        self.assertFalse(res.authenticated)
        self.assertIn("passkey requise", res.raison_refus)
        noeuds.assert_not_called()

    def test_compte_sans_passkey_reste_en_zkp_seul(self):
        res, _ = self.authentifier(self.requete("bob", NONCE_1, commitment="987654321"))
        self.assertTrue(res.authenticated, res.raison_refus)

    def test_assertion_d_une_autre_session_refusee(self):
        assertion = self.auth.signer(self.challenge(nonce=NONCE_2))
        res, _ = self.authentifier(self.requete("alice", NONCE_1, assertion))
        self.assertFalse(res.authenticated)

    def test_assertion_rejouee_refusee(self):
        assertion = self.auth.signer(self.challenge())
        self.assertTrue(self.authentifier(self.requete("alice", NONCE_1, assertion))[0].authenticated)
        res, _ = self.authentifier(self.requete("alice", NONCE_1, assertion))
        self.assertFalse(res.authenticated)

    def test_passkey_d_un_autre_compte_refusee(self):
        jwt_bob = "Bearer " + jwt_manager.generate_token("bob")
        auth_bob = AuthentificateurLogiciel()
        self.enregistrer(auth_bob, user="bob", jwt=jwt_bob)
        assertion = auth_bob.signer(self.challenge())
        res, _ = self.authentifier(self.requete("alice", NONCE_1, assertion))
        self.assertFalse(res.authenticated)
        self.assertIn("non associée", res.raison_refus)

    def test_signature_par_une_autre_cle_refusee(self):
        imposteur = AuthentificateurLogiciel()
        imposteur.credential_id = self.auth.credential_id
        imposteur.user_handle = self.auth.user_handle
        res, _ = self.authentifier(self.requete("alice", NONCE_1, imposteur.signer(self.challenge())))
        self.assertFalse(res.authenticated)

    def test_assertion_sans_verification_utilisateur_refusee(self):
        res, _ = self.authentifier(self.requete("alice", NONCE_1, self.auth.signer(self.challenge(), uv=False)))
        self.assertFalse(res.authenticated)

    def test_assertion_depuis_une_autre_origine_refusee(self):
        assertion = self.auth.signer(self.challenge(), origine="https://phishing.example")
        res, _ = self.authentifier(self.requete("alice", NONCE_1, assertion))
        self.assertFalse(res.authenticated)

    def test_user_handle_d_un_autre_utilisateur_refuse(self):
        assertion = self.auth.signer(self.challenge(), user_handle=webauthn_service.user_handle("bob"))
        res, _ = self.authentifier(self.requete("alice", NONCE_1, assertion))
        self.assertFalse(res.authenticated)

    def test_compteur_non_incremente_refuse(self):
        """Compteur qui ne progresse pas : authentificateur cloné suspecté."""
        self.authentifier(self.requete("alice", NONCE_1, self.auth.signer(self.challenge())))
        assertion = self.auth.signer(self.challenge(nonce=NONCE_2), incrementer=False)
        res, _ = self.authentifier(self.requete("alice", NONCE_2, assertion))
        self.assertFalse(res.authenticated)

    def test_mise_a_jour_concurrente_du_compteur_une_seule_reussit(self):
        cid = b64(self.auth.credential_id)
        self.assertTrue(store.update_webauthn_sign_count(cid, 0, 1))
        self.assertFalse(store.update_webauthn_sign_count(cid, 0, 1))

    def test_assertion_malformee_refusee(self):
        res, _ = self.authentifier(self.requete("alice", NONCE_1, {"rawId": b64(self.auth.credential_id)}))
        self.assertFalse(res.authenticated)

    def test_nonce_ne_revele_pas_les_passkeys_du_compte(self):
        from routes.nonce import get_nonce

        with patch("routes.nonce.request_nonce_from_node", return_value=(NONCE_1, int(time.time()) + 60)):
            avec = get_nonce("alice").webauthn
            sans = get_nonce("bob").webauthn
        self.assertEqual(set(avec), set(sans))
        self.assertNotIn("allowCredentials", avec)


class TestConfigurationWebAuthn(unittest.TestCase):
    def test_production_exige_rp_id_et_origines_https(self):
        base = {"FACEIN_ENV": "production"}
        with patch.dict(os.environ, {**base, "WEBAUTHN_RP_ID": "", "WEBAUTHN_ORIGINS": ""}):
            with self.assertRaises(RuntimeError):
                webauthn_service.verifier_configuration_webauthn()
        with patch.dict(os.environ, {**base, "WEBAUTHN_RP_ID": "facein.fr", "WEBAUTHN_ORIGINS": "http://facein.fr"}):
            with self.assertRaises(RuntimeError):
                webauthn_service.verifier_configuration_webauthn()
        with patch.dict(os.environ, {**base, "WEBAUTHN_RP_ID": "facein.fr", "WEBAUTHN_ORIGINS": "https://facein.fr"}):
            webauthn_service.verifier_configuration_webauthn()


if __name__ == "__main__":
    unittest.main()
