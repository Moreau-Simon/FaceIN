"""
Tests unitaires pour les services et composants de l'API Gateway FaceIn.
Exécutable avec pytest ou python3 -m unittest.
"""

import json
import asyncio
import os
import sys

# Forcer le backend mémoire et autoriser la simulation par défaut dans les tests unitaires
os.environ.setdefault("STORE_BACKEND", "memory")
os.environ.setdefault("ALLOW_MOCK_CONSENSUS", "true")

import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from fastapi import HTTPException

# Ajout du répertoire api et nodes/node au path pour les imports directs
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
NODES_DIR = os.path.join(os.path.dirname(API_DIR), "nodes", "node")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)
if NODES_DIR not in sys.path:
    sys.path.insert(0, NODES_DIR)

from models import (  # noqa: E402
    BN254_FIELD_ORDER,
    AuthenticateRequest,
    AuthenticateResponse,
    RegisterRequest,
    RegisterResponse,
    validate_bn254_element,
    validate_user_id_format,
)
from services import grpc_bridge, rate_limiter, store, zkp_verifier  # noqa: E402
import api.main as api_main  # noqa: E402


class TestStoreService(unittest.TestCase):
    """Tests du module store.py avec le backend mémoire."""

    def setUp(self):
        store.reset_store()
        self.storage = store.get_store()

    def tearDown(self):
        store.reset_store()

    def test_save_and_get_commitment(self):
        user_id = "alice"
        commitment = "12345678901234567890"

        self.assertIsNone(self.storage.get_engagement(user_id))

        self.storage.save_engagement(user_id, commitment)

        engagement = self.storage.get_engagement(user_id)
        self.assertIsNotNone(engagement)
        self.assertEqual(engagement["commitment"], commitment)

    def test_save_commitment_replaces_previous_commitment(self):
        user_id = "bob"

        self.storage.save_engagement(user_id, "1111111111")
        self.storage.save_engagement(user_id, "2222222222")

        engagement = self.storage.get_engagement(user_id)
        self.assertEqual(engagement["commitment"], "2222222222")

    def test_nonce_lifecycle_and_single_use(self):
        user_id = "charlie"
        nonce = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        expires_at = time.time() + 60.0

        self.storage.save_nonce(nonce, user_id, expires_at)

        # Première utilisation : nonce valide
        self.assertTrue(self.storage.consume_nonce(nonce, user_id))

        # Deuxième utilisation : nonce déjà consommé
        self.assertFalse(self.storage.consume_nonce(nonce, user_id))

    def test_expired_nonce(self):
        user_id = "david"
        nonce = "expired-nonce-000"
        expires_at = time.time() - 10.0

        self.storage.save_nonce(nonce, user_id, expires_at)

        self.assertFalse(self.storage.consume_nonce(nonce, user_id))

    def test_user_exists_independent_of_engagement_status(self):
        user_id = "elena"
        self.assertFalse(self.storage.user_exists(user_id))

        self.storage.save_engagement(user_id, "999999999")
        self.assertTrue(self.storage.user_exists(user_id))

        # Après révocation, l'utilisateur existe toujours dans le registre
        self.storage.revoke_engagement(user_id)
        self.assertIsNone(self.storage.get_engagement(user_id))
        self.assertTrue(self.storage.user_exists(user_id))

    def test_store_ping_and_close(self):
        self.assertTrue(self.storage.ping())
        self.storage.close()


class TestZkpVerifier(unittest.TestCase):
    """Tests du module de vérification ZKP et d'intégrité des signaux publics."""

    VALID_PROOF = {
        "pi_a": ["123", "456"],
        "pi_b": [["11", "22"], ["33", "44"]],
        "pi_c": ["789", "101"],
    }
    VALID_NONCE = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    VAL_INT = int(VALID_NONCE, 16)
    NONCE_HI = str(VAL_INT >> 128)
    NONCE_LO = str(VAL_INT & ((1 << 128) - 1))
    VALID_SIGNALS = ["123456789", "16000000", NONCE_HI, NONCE_LO]

    def test_zkp_mock_mode(self):
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"
        try:
            result = zkp_verifier.verify_proof(
                proof=self.VALID_PROOF,
                public_signals=self.VALID_SIGNALS,
            )
            self.assertTrue(result)
        finally:
            os.environ.pop("MOCK_ZKP_VERIFICATION", None)

    def test_missing_vk_returns_false(self):
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)
        result = zkp_verifier.verify_proof(
            proof=self.VALID_PROOF,
            public_signals=self.VALID_SIGNALS,
            verification_key_path="/non/existent/path/verification_key.json",
        )
        self.assertFalse(result)

    def test_public_signals_structure_validation(self):
        # Cardinalité incorrecte (moins de 4)
        ok, _ = zkp_verifier.validate_public_signals_structure(["123", "456"])
        self.assertFalse(ok)

        # Cardinalité incorrecte (plus de 4)
        ok, _ = zkp_verifier.validate_public_signals_structure(self.VALID_SIGNALS + ["extra"])
        self.assertFalse(ok)

        # Signal non numérique
        ok, _ = zkp_verifier.validate_public_signals_structure(["abc", "16000000", "1", "2"])
        self.assertFalse(ok)

        # Signal avec zéros non significatifs en tête (non canonique)
        ok, _ = zkp_verifier.validate_public_signals_structure(["0123", "16000000", "1", "2"])
        self.assertFalse(ok)

        # Signal hors corps BN254
        ok, _ = zkp_verifier.validate_public_signals_structure(
            [str(zkp_verifier.BN254_PRIME + 10), "16000000", "1", "2"]
        )
        self.assertFalse(ok)

        # Valide
        ok, err = zkp_verifier.validate_public_signals_structure(self.VALID_SIGNALS)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_public_signals_integrity_validation(self):
        # 1. Valide nominal
        ok, err = zkp_verifier.validate_public_signals_integrity(
            public_signals=self.VALID_SIGNALS,
            expected_commitment="123456789",
            nonce_hex=self.VALID_NONCE,
            max_threshold=16000000,
        )
        self.assertTrue(ok)

        # 2. Incohérence d'engagement
        ok, err = zkp_verifier.validate_public_signals_integrity(
            public_signals=self.VALID_SIGNALS,
            expected_commitment="999999999",
            nonce_hex=self.VALID_NONCE,
            max_threshold=16000000,
        )
        self.assertFalse(ok)
        self.assertIn("L'engagement biométrique de référence ne correspond pas", err)

        # 3. Manipulation du seuil par le client
        signaux_seuil_altere = list(self.VALID_SIGNALS)
        signaux_seuil_altere[1] = "99999999"
        ok, err = zkp_verifier.validate_public_signals_integrity(
            public_signals=signaux_seuil_altere,
            expected_commitment="123456789",
            nonce_hex=self.VALID_NONCE,
            max_threshold=16000000,
        )
        self.assertFalse(ok)
        self.assertIn("Seuil biométrique non conforme", err)

        # 4. Nonce mismatch
        ok, err = zkp_verifier.validate_public_signals_integrity(
            public_signals=self.VALID_SIGNALS,
            expected_commitment="123456789",
            nonce_hex="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            max_threshold=16000000,
        )
        self.assertFalse(ok)
        self.assertIn("défi nonce", err)

    def test_proof_structure_validation(self):
        # Composante manquante
        ok, _ = zkp_verifier.validate_proof_structure({"pi_a": ["1", "2"], "pi_b": [["1", "2"]]})
        self.assertFalse(ok)

        # Non-dictionnaire
        ok, _ = zkp_verifier.validate_proof_structure("not-a-dict")
        self.assertFalse(ok)

        # Valide
        ok, _ = zkp_verifier.validate_proof_structure(self.VALID_PROOF)
        self.assertTrue(ok)

        # Payload trop volumineux (> 64 Ko)
        huge_proof = dict(self.VALID_PROOF)
        huge_proof["junk"] = "a" * (70 * 1024)
        ok, err = zkp_verifier.validate_proof_structure(huge_proof)
        self.assertFalse(ok)
        self.assertIn("trop volumineux", err)


class TestGrpcBridge(unittest.TestCase):
    """Tests du pont client gRPC et du consensus."""

    def setUp(self):
        grpc_bridge.fermer_canaux()

    def tearDown(self):
        grpc_bridge.fermer_canaux()

    def test_verify_on_nodes_fallback_mock(self):
        with patch.dict(os.environ, {"ALLOW_MOCK_CONSENSUS": "true"}):
            result = grpc_bridge.verify_on_nodes(
                user_id="alice",
                proof_json_str=json.dumps({"test": True}),
                nonce="0123456789abcdef0123456789abcdef",
            )
            self.assertIn("consensus", result)
            self.assertIn("votes", result)
            self.assertIn("majority", result)
            self.assertIsInstance(result["consensus"], bool)
            self.assertEqual(len(result["votes"]), 3)

    def test_request_nonce_from_node_fallback(self):
        nonce, exp = grpc_bridge.request_nonce_from_node(user_id="alice")
        self.assertIsNone(nonce)
        self.assertIsNone(exp)

    def test_api_lifespan_ferme_les_canaux_partages(self):
        """Vérifie que les canaux gRPC partagés sont fermés en fin de cycle de vie."""
        channel = Mock()
        mock_grpc = grpc_bridge.grpc or Mock()
        mock_grpc.insecure_channel = Mock(return_value=channel)
        mock_grpc.ssl_channel_credentials = Mock()
        mock_grpc.secure_channel = Mock(return_value=channel)

        # Créer le canal dans le registre partagé, puis appeler fermer_canaux() directement
        # (reproduit ce que le lifespan fait au shutdown)
        with patch.dict(os.environ, {"TLS_ENABLED": "false"}), \
             patch.object(grpc_bridge, "grpc", mock_grpc):
            grpc_bridge._creer_canal("unused-target:50051")
            grpc_bridge.fermer_canaux()

        mock_grpc.insecure_channel.assert_called_once_with(
            "unused-target:50051",
            options=grpc_bridge.GRPC_CHANNEL_OPTIONS,
        )
        channel.close.assert_called_once_with()

    def test_api_uses_mutual_tls_for_nonce_and_verification(self):
        with tempfile.TemporaryDirectory() as cert_dir:
            paths = {
                "TLS_CA_CERT": os.path.join(cert_dir, "ca.crt"),
                "TLS_CERT": os.path.join(cert_dir, "api.crt"),
                "TLS_KEY": os.path.join(cert_dir, "api.key"),
            }
            contents = {
                paths["TLS_CA_CERT"]: b"ca",
                paths["TLS_CERT"]: b"api certificate",
                paths["TLS_KEY"]: b"api private key",
            }
            for path, content in contents.items():
                with open(path, "wb") as cert_file:
                    cert_file.write(content)

            responses = [
                SimpleNamespace(
                    accepte=True,
                    token="token",
                    raison_refus="",
                ),
                SimpleNamespace(nonce="nonce-123", expiration_timestamp=123456),
            ]

            class VerificationStub:
                def __init__(self, channel):
                    self.channel = channel

                def VerifierPreuve(self, request, timeout):
                    return responses.pop(0)

                def DemanderNonce(self, request, timeout):
                    return responses.pop(0)

            credentials = object()
            channel = SimpleNamespace(close=Mock())
            mock_grpc = Mock()
            mock_grpc.ssl_channel_credentials = Mock(return_value=credentials)
            mock_grpc.secure_channel = Mock(return_value=channel)
            mock_stub = Mock(return_value=VerificationStub(channel))

            with patch.dict(
                os.environ, {**paths, "TLS_ENABLED": "true"}, clear=False
            ), patch.object(grpc_bridge, "grpc", mock_grpc), patch.object(
                grpc_bridge, "verification_pb2", SimpleNamespace(DemandeVerification=Mock(return_value=Mock()), DemandeNonce=Mock(return_value=Mock())),
            ), patch.object(
                grpc_bridge,
                "verification_pb2_grpc",
                SimpleNamespace(VerificationServiceStub=mock_stub),
            ):
                result = grpc_bridge.verify_on_nodes(
                    "alice",
                    json.dumps({"proof": "test"}),
                    "0123456789abcdef0123456789abcdef",
                    nodes=[{"id": "node-a", "host": "node-a", "port": 50051}],
                )
                nonce, expiration = grpc_bridge.request_nonce_from_node(
                    "alice",
                    nodes=[{"id": "node-a", "host": "node-a", "port": 50051}],
                )

            self.assertTrue(result["consensus"])
            self.assertEqual((nonce, expiration), ("nonce-123", 123456))
            self.assertEqual(mock_grpc.secure_channel.call_count, 1)
            self.assertEqual(
                [call.args[0] for call in mock_grpc.secure_channel.call_args_list],
                ["node-a:50051"],
            )
            self.assertEqual(mock_grpc.ssl_channel_credentials.call_count, 1)
            self.assertEqual(
                mock_grpc.ssl_channel_credentials.call_args.kwargs,
                {
                    "root_certificates": b"ca",
                    "private_key": b"api private key",
                    "certificate_chain": b"api certificate",
                },
            )
            self.assertEqual(
                mock_grpc.secure_channel.call_args.kwargs["options"],
                grpc_bridge.GRPC_CHANNEL_OPTIONS,
            )
            grpc_bridge.fermer_canaux()
            channel.close.assert_called_once_with()


def _build_hs256_jwt_shim():
    """Shim HS256 complet compatible PyJWT pour exécution sans dépendance externe."""
    import base64
    import hashlib
    import hmac

    class InvalidTokenError(Exception):
        pass

    class ExpiredSignatureError(InvalidTokenError):
        pass

    class InvalidIssuerError(InvalidTokenError):
        pass

    class InvalidAudienceError(InvalidTokenError):
        pass

    class MissingRequiredClaimError(InvalidTokenError):
        pass

    def _b64enc(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _b64dec(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def encode(payload, key, algorithm="HS256"):
        header = _b64enc(json.dumps({"alg": algorithm, "typ": "JWT"}, separators=(",", ":")).encode())
        body = _b64enc(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header}.{body}".encode()
        sig = hmac.new(key.encode(), signing_input, hashlib.sha256).digest()
        return f"{header}.{body}.{_b64enc(sig)}"

    def decode(token, key, algorithms=None, issuer=None, audience=None, options=None):
        parts = token.split(".")
        if len(parts) != 3:
            raise InvalidTokenError("Format JWT invalide")
        header_b64, body_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{body_b64}".encode()
        expected_sig = hmac.new(key.encode(), signing_input, hashlib.sha256).digest()
        try:
            actual_sig = _b64dec(sig_b64)
        except Exception as exc:
            raise InvalidTokenError("Signature illisible") from exc
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise InvalidTokenError("Signature invalide")

        try:
            payload = json.loads(_b64dec(body_b64).decode())
        except Exception as exc:
            raise InvalidTokenError("Payload illisible") from exc

        req = (options or {}).get("require", [])
        for claim in req:
            if claim not in payload:
                raise MissingRequiredClaimError(claim)

        if "exp" in payload and float(payload["exp"]) < time.time():
            raise ExpiredSignatureError("Token expiré")
        if issuer is not None and payload.get("iss") != issuer:
            raise InvalidIssuerError("Émetteur invalide")
        if audience is not None and payload.get("aud") != audience:
            raise InvalidAudienceError("Audience invalide")
        return payload

    return SimpleNamespace(
        encode=encode,
        decode=decode,
        InvalidTokenError=InvalidTokenError,
        ExpiredSignatureError=ExpiredSignatureError,
        InvalidIssuerError=InvalidIssuerError,
        InvalidAudienceError=InvalidAudienceError,
        MissingRequiredClaimError=MissingRequiredClaimError,
    )


class TestJwtManager(unittest.TestCase):
    """Tests complets pour le gestionnaire de tokens JWT et la gestion des sessions."""

    def setUp(self):
        from services import jwt_manager
        store.reset_store()
        jwt_manager.reset_blacklist()
        self._orig_jwt = jwt_manager.jwt
        if jwt_manager.jwt is None:
            jwt_manager.jwt = _build_hs256_jwt_shim()

    def tearDown(self):
        from services import jwt_manager
        jwt_manager.jwt = self._orig_jwt
        jwt_manager.reset_blacklist()
        store.reset_store()

    def test_jwt_valid_claims(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice", audience="facein-web")
            payload = jwt_manager.verify_token(token, audience="facein-web")
            self.assertIsNotNone(payload)
            self.assertEqual(payload["sub"], "alice")
            self.assertEqual(payload["iss"], "facein-api")
            self.assertEqual(payload["aud"], "facein-web")
            self.assertIn("iat", payload)
            self.assertIn("exp", payload)
            self.assertIn("jti", payload)
            self.assertEqual(payload["ver"], "1")

    def test_jwt_expired_rejected(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice", expiration_seconds=-10)
            self.assertIsNone(jwt_manager.verify_token(token))

    def test_jwt_tampered_rejected(self):
        from services import jwt_manager
        import base64
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice")
            h, _, s = token.split(".")
            tampered_body = base64.urlsafe_b64encode(
                json.dumps({"sub": "admin", "iss": "facein-api", "aud": "facein-web",
                            "iat": int(time.time()), "exp": int(time.time()) + 3600, "jti": "x"}).encode()
            ).rstrip(b"=").decode()
            self.assertIsNone(jwt_manager.verify_token(f"{h}.{tampered_body}.{s}"))

    def test_jwt_wrong_signature_rejected(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "cle-a-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice")
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "cle-b-autre-secret-256-bits-minimum"}):
            self.assertIsNone(jwt_manager.verify_token(token))

    def test_jwt_wrong_issuer_rejected(self):
        from services import jwt_manager
        now = int(time.time())
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            forged = jwt_manager.jwt.encode(
                {"sub": "alice", "iss": "evil-issuer", "aud": "facein-web",
                 "iat": now, "exp": now + 3600, "jti": "jti-1"},
                "test-secret-key-256-bits-minimum-ok",
                algorithm="HS256",
            )
            self.assertIsNone(jwt_manager.verify_token(forged))

    def test_jwt_wrong_audience_rejected(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice", audience="facein-mobile")
            self.assertIsNone(jwt_manager.verify_token(token, audience="facein-web"))

    def test_jwt_revoked_rejected(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice", audience="facein-web")
            payload = jwt_manager.verify_token(token, audience="facein-web")
            self.assertIsNotNone(payload)

            self.assertTrue(jwt_manager.revoquer_token(token, audience="facein-web"))
            self.assertIsNone(jwt_manager.verify_token(token, audience="facein-web"))
            self.assertTrue(store.is_jti_revoked(payload["jti"]))

    def test_jwt_missing_key_in_production_raises(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_ENV": "production", "JWT_SECRET_KEY": ""}):
            with self.assertRaises(RuntimeError):
                jwt_manager.generate_token("alice")

    def test_jwt_key_rotation(self):
        from services import jwt_manager
        old_key = "old-secret-key-256-bits-minimum-ok"
        new_key = "new-secret-key-256-bits-minimum-ok"
        with patch.dict(os.environ, {"JWT_SECRET_KEY": old_key}):
            old_token = jwt_manager.generate_token("alice")

        with patch.dict(os.environ, {"JWT_SECRET_KEY": new_key, "JWT_SECRET_KEY_PREVIOUS": old_key}):
            # L'ancien token reste valide pendant la rotation
            self.assertIsNotNone(jwt_manager.verify_token(old_token))
            # Un nouveau token est signé avec la nouvelle clé
            new_token = jwt_manager.generate_token("bob")
            self.assertIsNotNone(jwt_manager.verify_token(new_token))

        # Sans l'ancienne clé configurée, l'ancien token est rejeté
        with patch.dict(os.environ, {"JWT_SECRET_KEY": new_key, "JWT_SECRET_KEY_PREVIOUS": ""}):
            self.assertIsNone(jwt_manager.verify_token(old_token))
            self.assertIsNotNone(jwt_manager.verify_token(new_token))

    def test_jwt_service_authorization(self):
        from services import jwt_manager
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-256-bits-minimum-ok"}):
            token = jwt_manager.generate_token("alice", audience="facein-partner")
            store.set_service_authorization("alice", "facein-partner", "actif")
            self.assertIsNotNone(jwt_manager.verify_service_access(token, "facein-partner"))

            # Révocation de l'autorisation pour ce service
            store.set_service_authorization("alice", "facein-partner", "revoque")
            self.assertIsNone(jwt_manager.verify_service_access(token, "facein-partner"))


class TestAuthenticateLogic(unittest.TestCase):
    """Tests du flux d'authentification biométrique ZKP."""

    VALID_PROOF = {
        "pi_a": ["123", "456"],
        "pi_b": [["11", "22"], ["33", "44"]],
        "pi_c": ["789", "101"],
    }
    DEFAULT_SEUIL = "16000000"

    def setUp(self):
        store.reset_store()
        self.storage = store.get_store()
        rate_limiter.reset_rate_limiter()
        self.valid_nonce = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def tearDown(self):
        store.reset_store()
        rate_limiter.reset_rate_limiter()

    def _signals_for(self, commitment, nonce=None, seuil=None):
        n = nonce or self.valid_nonce
        val = int(n, 16)
        hi = str(val >> 128)
        lo = str(val & ((1 << 128) - 1))
        return [str(commitment), str(seuil or self.DEFAULT_SEUIL), hi, lo]

    def test_auth_step1_malformed_nonce_rejected(self):
        from routes.authenticate import authenticate

        # Nonce trop court (32 chars au lieu de 64 chars / 256 bits)
        req = AuthenticateRequest(
            user_id="user1",
            proof=self.VALID_PROOF,
            public_signals=["123456789", "16000000", "1", "2"],
            nonce="0123456789abcdef0123456789abcdef",
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertFalse(res.success)
        self.assertEqual(res.reason, "Nonce malformé (attendu : 64 caractères hexadécimaux)")
        self.assertEqual(res.raison_refus, "Nonce malformé")

    def test_auth_fails_when_user_not_registered(self):
        from routes.authenticate import authenticate

        req = AuthenticateRequest(
            user_id="user_unregistered",
            proof=self.VALID_PROOF,
            public_signals=self._signals_for("123456789"),
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertFalse(res.success)
        self.assertEqual(res.reason, "Utilisateur non enregistré ou engagement introuvable")

    def test_auth_fails_when_threshold_altered(self):
        from routes.authenticate import authenticate

        user_id = "user_tamper_thresh"
        commitment = "123456789"
        self.storage.save_engagement(user_id, commitment)

        req = AuthenticateRequest(
            user_id=user_id,
            proof=self.VALID_PROOF,
            public_signals=self._signals_for(commitment, seuil="99999999"),
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertIn("Seuil biométrique non conforme", res.reason)

    def test_auth_fails_when_commitment_mismatch(self):
        from routes.authenticate import authenticate

        user_id = "user_mismatch_comm"
        self.storage.save_engagement(user_id, "123456789")

        req = AuthenticateRequest(
            user_id=user_id,
            proof=self.VALID_PROOF,
            public_signals=self._signals_for("999999999"),
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertIn("L'engagement biométrique de référence ne correspond pas", res.reason)

    def test_auth_fails_when_nonce_mismatch(self):
        from routes.authenticate import authenticate

        user_id = "user_mismatch_nonce"
        commitment = "123456789"
        self.storage.save_engagement(user_id, commitment)

        other_nonce = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        req = AuthenticateRequest(
            user_id=user_id,
            proof=self.VALID_PROOF,
            public_signals=self._signals_for(commitment, nonce=other_nonce),
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertIn("défi nonce", res.reason)

    def test_auth_step2_zkp_failure(self):
        from routes.authenticate import authenticate

        user_id = "user_step2"
        commitment = "123456789"
        self.storage.save_engagement(user_id, commitment)

        # Désactiver le mock ZKP pour forcer le rejet local snarkjs
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)

        req = AuthenticateRequest(
            user_id=user_id,
            proof=self.VALID_PROOF,
            public_signals=self._signals_for(commitment),
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertFalse(res.success)
        self.assertEqual(res.reason, "Échec de la vérification locale de la preuve ZKP")

    def test_auth_step3_consensus_failure(self):
        from routes.authenticate import authenticate

        user_id = "user_step3"
        commitment = "123456789"
        self.storage.save_engagement(user_id, commitment)

        # Activer le mock ZKP
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"

        # Simuler un refus de consensus gRPC (ex: nonce déjà consommé sur les nœuds)
        with patch(
            "routes.authenticate.verify_on_nodes",
            return_value={
                "consensus": False,
                "majority": "0/3",
                "reason": "nonce invalide ou expiré",
            },
        ):
            req = AuthenticateRequest(
                user_id=user_id,
                proof=self.VALID_PROOF,
                public_signals=self._signals_for(commitment),
                nonce=self.valid_nonce,
            )
            res = authenticate(req)
            self.assertFalse(res.authenticated)
            self.assertFalse(res.success)
            self.assertEqual(res.reason, "Consensus non atteint par le réseau de pairs")
            self.assertEqual(res.raison_refus, "nonce invalide ou expiré")

    def test_auth_success(self):
        from routes.authenticate import authenticate
        from services import jwt_manager

        user_id = "user_success"
        commitment = "123456789"
        self.storage.save_engagement(user_id, commitment)

        # Activer le mock ZKP
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"

        mock_jwt = Mock()
        mock_jwt.encode.return_value = "eyJheader.payload.signature"
        original_jwt = jwt_manager.jwt
        jwt_manager.jwt = mock_jwt

        try:
            with patch(
                "routes.authenticate.verify_on_nodes",
                return_value={
                    "consensus": True,
                    "majority": "3/3",
                    "reason": "",
                },
            ):
                req = AuthenticateRequest(
                    user_id=user_id,
                    proof=self.VALID_PROOF,
                    public_signals=self._signals_for(commitment),
                    nonce=self.valid_nonce,
                )
                res = authenticate(req)
                self.assertTrue(res.authenticated)
                self.assertTrue(res.success)
                self.assertEqual(res.token, "eyJheader.payload.signature")
                self.assertIsNone(res.reason)
                self.assertEqual(res.message, "Authentification réussie")
        finally:
            jwt_manager.jwt = original_jwt
            os.environ.pop("MOCK_ZKP_VERIFICATION", None)

    def test_auth_frontend_contract_compliance(self):
        from routes.authenticate import authenticate

        user_id = "user_contract"
        req = AuthenticateRequest(
            user_id=user_id,
            proof=self.VALID_PROOF,
            public_signals=["123456"],
            nonce=self.valid_nonce,
        )
        res = authenticate(req)
        # Le frontend teste authResult.raison_refus || authResult.message
        self.assertIsNotNone(res.raison_refus)
        self.assertIsNotNone(res.message)
        self.assertIn("success", res.model_dump())
        self.assertIn("authenticated", res.model_dump())


class TestRegisterAndNonceRoutes(unittest.TestCase):
    """Tests des routes register et nonce."""

    def setUp(self):
        store.reset_store()
        self.storage = store.get_store()
        rate_limiter.reset_rate_limiter()

    def tearDown(self):
        store.reset_store()
        rate_limiter.reset_rate_limiter()

    def test_register_success(self):
        from routes.register import register

        valid_commitment = "12345678901234567890"
        req = RegisterRequest(user_id="new_user", commitment=valid_commitment)
        res = register(req)
        self.assertTrue(res.success)
        self.assertEqual(res.message, "Engagement enregistré")
        self.assertIsNotNone(self.storage.get_engagement("new_user"))

    def test_register_conflict(self):
        from routes.register import register

        valid_commitment = "12345678901234567890"
        req = RegisterRequest(user_id="duplicate_user", commitment=valid_commitment)
        register(req)

        with self.assertRaises(HTTPException) as ctx:
            register(req)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_register_store_dependency_error(self):
        from routes.register import register

        with patch("routes.register.save_commitment", side_effect=RuntimeError("DB disconnected")):
            req = RegisterRequest(user_id="alice_err", commitment="12345")
            with self.assertRaises(HTTPException) as ctx:
                register(req)
            self.assertEqual(ctx.exception.status_code, 500)

    def test_register_propagates_to_nodes(self):
        from routes.register import register

        with patch("routes.register.propagate_commitment_to_nodes") as mock_prop:
            mock_prop.return_value = {"quorum": True, "majority": "3/3"}
            req = RegisterRequest(user_id="new_user2", commitment="12345678901234567890")
            res = register(req)
            self.assertTrue(res.success)
            mock_prop.assert_called_once_with("new_user2", "12345678901234567890")

    def test_register_success_even_if_propagation_fails(self):
        from routes.register import register

        with patch("routes.register.propagate_commitment_to_nodes", side_effect=Exception("gRPC down")):
            req = RegisterRequest(user_id="new_user3", commitment="12345678901234567890")
            res = register(req)
            self.assertTrue(res.success)  # propagation non bloquante

    def test_get_nonce_success(self):
        from routes.nonce import get_nonce

        mock_nonce = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        mock_exp = int(time.time() + 60)

        with patch("routes.nonce.request_nonce_from_node", return_value=(mock_nonce, mock_exp)):
            res = get_nonce("test_user_nonce")
            self.assertIsNotNone(res.nonce)
            self.assertTrue(res.success)
            self.assertEqual(len(res.nonce), 64)  # 256 bits = 64 caractères hex
            self.assertEqual(res.nonce, mock_nonce)
            self.assertGreater(res.expires_at, time.time())
            self.assertIsInstance(res.defis, list)

    def test_get_nonce_nodes_unavailable_raises_503(self):
        from routes.nonce import get_nonce

        with patch("routes.nonce.request_nonce_from_node", return_value=(None, None)):
            with self.assertRaises(HTTPException) as ctx:
                get_nonce("test_user_no_nodes")
            self.assertEqual(ctx.exception.status_code, 503)


class TestNonceSecurity(unittest.TestCase):
    """Tests de sécurité avancés pour les nonces 256 bits."""

    def test_nonce_store_emits_256_bit_hex_nonce(self):
        from verification.nonces import NonceStore
        store_inst = NonceStore(duree_s=60)
        nonce, exp_ms = store_inst.emettre("alice", "facein-web")

        self.assertEqual(len(nonce), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in nonce))
        self.assertGreater(exp_ms, int(time.time() * 1000))

    def test_nonce_single_use_strictly_enforced(self):
        from verification.nonces import NonceStore
        store_inst = NonceStore()
        nonce, _ = store_inst.emettre("alice", "facein-web")

        # Première consommation : valide
        self.assertTrue(store_inst.consommer("alice", nonce, "facein-web"))
        # Seconde consommation : rejet (rejeu impossible)
        self.assertFalse(store_inst.consommer("alice", nonce, "facein-web"))

    def test_nonce_service_cible_isolation(self):
        from verification.nonces import NonceStore
        store_inst = NonceStore()
        # Émis pour facein-web
        nonce, _ = store_inst.emettre("bob", "facein-web")

        # Tentative de consommation pour facein-mobile -> rejeté
        self.assertFalse(store_inst.consommer("bob", nonce, "facein-mobile"))
        # Le nonce a été invalidé par la tentative
        self.assertFalse(store_inst.consommer("bob", nonce, "facein-web"))

    def test_nonce_expiration_enforced(self):
        from verification.nonces import NonceStore
        maintenant = [100.0]
        store_inst = NonceStore(duree_s=60, horloge=lambda: maintenant[0])
        nonce, _ = store_inst.emettre("charlie", "facein-web")

        # Avance le temps de 61 secondes
        maintenant[0] = 161.0
        self.assertFalse(store_inst.consommer("charlie", nonce, "facein-web"))

    def test_wrong_user_nonce_rejected(self):
        from verification.nonces import NonceStore
        store_inst = NonceStore()
        nonce, _ = store_inst.emettre("alice", "facein-web")

        self.assertFalse(store_inst.consommer("eve", nonce, "facein-web"))
        # Eve ne peut pas consommer le nonce d'Alice, et le nonce est invalidé
        self.assertFalse(store_inst.consommer("alice", nonce, "facein-web"))


class TestStrictValidationAndSecurity(unittest.TestCase):
    """Tests des règles de validation Pydantic, CORS et Rate Limiting."""

    def setUp(self):
        rate_limiter.reset_rate_limiter()

    def tearDown(self):
        rate_limiter.reset_rate_limiter()

    def test_valid_user_ids(self):
        self.assertEqual(validate_user_id_format("alice"), "alice")
        self.assertEqual(validate_user_id_format("user_123-abc"), "user_123-abc")

    def test_malformed_user_ids(self):
        invalid_ids = ["ab", "a" * 65, "user@test", "user\nid", "<script>", "   "]
        for uid in invalid_ids:
            with self.assertRaises(ValueError):
                validate_user_id_format(uid)

    def test_valid_bn254_commitment(self):
        self.assertEqual(validate_bn254_element("0"), "0")
        self.assertEqual(validate_bn254_element("123456"), "123456")
        hex_val = hex(BN254_FIELD_ORDER - 1)
        self.assertEqual(validate_bn254_element(hex_val), hex_val)

    def test_invalid_bn254_commitment(self):
        # Supérieur à l'ordre du corps BN254
        with self.assertRaises(ValueError):
            validate_bn254_element(str(BN254_FIELD_ORDER))
        # Non numérique
        with self.assertRaises(ValueError):
            validate_bn254_element("not_a_number")

    def test_rate_limiting_enforcement(self):
        limiter = rate_limiter.SlidingWindowRateLimiter()
        # 3 requêtes max par tranche de 60 secondes
        allowed, _ = limiter.check_rate_limit("client-1", max_requests=3, window_seconds=60)
        self.assertTrue(allowed)
        allowed, _ = limiter.check_rate_limit("client-1", max_requests=3, window_seconds=60)
        self.assertTrue(allowed)
        allowed, _ = limiter.check_rate_limit("client-1", max_requests=3, window_seconds=60)
        self.assertTrue(allowed)
        # 4e requête -> doit être rejetée
        allowed, retry_after = limiter.check_rate_limit("client-1", max_requests=3, window_seconds=60)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_cors_configuration(self):
        # Vérifie que le middleware CORS est bien configuré sur l'application FastAPI
        cors_middleware = None
        for middleware in api_main.app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break
        self.assertIsNotNone(cors_middleware, "CORSMiddleware doit être configuré")
        options = cors_middleware.kwargs
        self.assertIn("http://localhost:3000", options.get("allow_origins", []))
        self.assertIn("http://localhost:8000", options.get("allow_origins", []))
        self.assertTrue(options.get("allow_credentials"))

    def test_health_check_endpoint(self):
        # Appel direct de la fonction health_check
        res = api_main.health_check()
        self.assertEqual(res.statut, "en_ligne")
        self.assertEqual(res.service, "FaceIn API Gateway")
        self.assertIn(res.stockage, ("memory", "postgres"))
        self.assertGreaterEqual(res.noeuds_configures, 3)

    def test_health_check_endpoint_degraded_when_store_down(self):
        mock_broken_store = Mock()
        mock_broken_store.ping.return_value = False
        with patch("api.main.get_store", return_value=mock_broken_store):
            res = api_main.health_check()
            self.assertEqual(res.statut, "degrade")


if __name__ == "__main__":
    unittest.main()
