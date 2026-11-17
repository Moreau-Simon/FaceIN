"""
Tests unitaires pour les services et composants de l'API Gateway FaceIn.
Exécutable avec pytest ou python3 -m unittest.
"""

import json
import asyncio
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

# Ajout du répertoire api au path pour les imports directs
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Simulation de fastapi et pydantic si exécuté hors conteneur (ex: environnement hôte sans pip)
try:
    import fastapi
    import pydantic
except ImportError:
    from unittest.mock import MagicMock

    class _MockRouter:
        def post(self, *args, **kwargs):
            return lambda fn: fn

        def get(self, *args, **kwargs):
            return lambda fn: fn

    mock_fastapi = MagicMock()
    mock_fastapi.APIRouter = _MockRouter
    mock_pydantic = MagicMock()

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _field(*args, **kwargs):
        return None

    mock_pydantic.BaseModel = _BaseModel
    mock_pydantic.Field = _field

    sys.modules["fastapi"] = mock_fastapi
    sys.modules["fastapi.middleware.cors"] = MagicMock()
    sys.modules["pydantic"] = mock_pydantic

from services import grpc_bridge, store, zkp_verifier  # noqa: E402
import api.main as api_main  # noqa: E402



class TestStoreService(unittest.TestCase):
    """Tests du module store.py (stockage SQLite des engagements et nonces)."""

    def setUp(self):
        # Utilisation d'un fichier SQLite temporaire isolé pour chaque test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        store.init_db(self.temp_db_path)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_save_and_get_commitment(self):
        user_id = "alice"
        commitment = "0x123456789abcdef"

        self.assertFalse(store.user_exists(user_id, self.temp_db_path))
        self.assertIsNone(store.get_commitment(user_id, self.temp_db_path))

        store.save_commitment(user_id, commitment, self.temp_db_path)

        self.assertTrue(store.user_exists(user_id, self.temp_db_path))
        self.assertEqual(store.get_commitment(user_id, self.temp_db_path), commitment)

    def test_save_duplicate_commitment_raises_error(self):
        user_id = "bob"
        commitment = "0xabc123"

        store.save_commitment(user_id, commitment, self.temp_db_path)
        with self.assertRaises(Exception):
            store.save_commitment(user_id, commitment, self.temp_db_path)

    def test_nonce_lifecycle_and_single_use(self):
        user_id = "charlie"
        nonce = "test-nonce-12345"
        expires_at = time.time() + 60.0  # Expire dans 60 secondes

        store.save_nonce(nonce, user_id, expires_at, self.temp_db_path)

        # Première vérification : doit être valide
        self.assertTrue(store.verify_nonce(nonce, user_id, self.temp_db_path))

        # Deuxième vérification (rejeu) : doit être invalide car supprimé
        self.assertFalse(store.verify_nonce(nonce, user_id, self.temp_db_path))

    def test_expired_nonce(self):
        user_id = "david"
        nonce = "expired-nonce-000"
        expires_at = time.time() - 10.0  # Expiré il y a 10 secondes

        store.save_nonce(nonce, user_id, expires_at, self.temp_db_path)

        # Vérification d'un nonce expiré : doit retourner False
        self.assertFalse(store.verify_nonce(nonce, user_id, self.temp_db_path))


class TestZkpVerifier(unittest.TestCase):
    """Tests du module de vérification ZKP."""

    def test_zkp_mock_mode(self):
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"
        try:
            result = zkp_verifier.verify_proof(
                proof={"pi_a": []},
                public_signals=["0x123", "1000"],
            )
            self.assertTrue(result)
        finally:
            os.environ.pop("MOCK_ZKP_VERIFICATION", None)

    def test_missing_vk_returns_false(self):
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)
        result = zkp_verifier.verify_proof(
            proof={"pi_a": []},
            public_signals=["0x123"],
            verification_key_path="/non/existent/path/verification_key.json",
        )
        self.assertFalse(result)


class TestGrpcBridge(unittest.TestCase):
    """Tests du pont client gRPC et du consensus."""

    def setUp(self):
        grpc_bridge.fermer_canaux()

    def tearDown(self):
        grpc_bridge.fermer_canaux()

    def test_verify_on_nodes_fallback_mock(self):
        # Lorsque les serveurs gRPC ne sont pas démarrés, verify_on_nodes doit gérer
        # l'absence de réseau avec le mode de test initial sans crasher.
        result = grpc_bridge.verify_on_nodes(
            user_id="alice",
            proof_json_str=json.dumps({"test": True}),
            nonce="nonce-123",
        )
        self.assertIn("consensus", result)
        self.assertIn("votes", result)
        self.assertIn("majority", result)
        self.assertIsInstance(result["consensus"], bool)
        self.assertEqual(len(result["votes"]), 3)

    def test_request_nonce_from_node_fallback(self):
        # En l'absence de noeuds gRPC actifs, request_nonce_from_node retourne (None, None)
        nonce, exp = grpc_bridge.request_nonce_from_node(user_id="alice")
        self.assertIsNone(nonce)
        self.assertIsNone(exp)

    def test_api_lifespan_ferme_les_canaux_partages(self):
        async def arreter_api():
            async with api_main.lifespan(api_main.app):
                pass

        channel = Mock()
        with patch.dict(os.environ, {"TLS_ENABLED": "false"}), patch.object(
            grpc_bridge.grpc,
            "insecure_channel",
            return_value=channel,
        ) as insecure_channel:
            grpc_bridge._creer_canal("unused-target:50051")
            asyncio.run(arreter_api())

        insecure_channel.assert_called_once_with(
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
            with patch.dict(
                os.environ, {**paths, "TLS_ENABLED": "true"}, clear=False
            ), patch.object(
                grpc_bridge.grpc,
                "ssl_channel_credentials",
                return_value=credentials,
            ) as ssl_credentials, patch.object(
                grpc_bridge.grpc,
                "secure_channel",
                return_value=channel,
            ) as secure_channel, patch.object(
                grpc_bridge.verification_pb2_grpc,
                "VerificationServiceStub",
                VerificationStub,
            ):
                result = grpc_bridge.verify_on_nodes(
                    "alice",
                    json.dumps({"proof": "test"}),
                    "nonce-123",
                    nodes=[{"id": "node-a", "host": "node-a", "port": 50051}],
                )
                nonce, expiration = grpc_bridge.request_nonce_from_node(
                    "alice",
                    nodes=[{"id": "node-a", "host": "node-a", "port": 50051}],
                )

            self.assertTrue(result["consensus"])
            self.assertEqual((nonce, expiration), ("nonce-123", 123456))
            self.assertEqual(secure_channel.call_count, 1)
            self.assertEqual(
                [call.args[0] for call in secure_channel.call_args_list],
                ["node-a:50051"],
            )
            self.assertEqual(ssl_credentials.call_count, 1)
            self.assertEqual(
                ssl_credentials.call_args.kwargs,
                {
                    "root_certificates": b"ca",
                    "private_key": b"api private key",
                    "certificate_chain": b"api certificate",
                },
            )
            self.assertEqual(
                secure_channel.call_args.kwargs["options"],
                grpc_bridge.GRPC_CHANNEL_OPTIONS,
            )
            grpc_bridge.fermer_canaux()
            channel.close.assert_called_once_with()


class TestJwtManager(unittest.TestCase):
    """Tests pour le gestionnaire de tokens JWT."""

    def test_jwt_generation_and_verification_mocked(self):
        from unittest.mock import MagicMock
        from services import jwt_manager

        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "eyJfake.jwt.token"
        mock_jwt.decode.return_value = {"user_id": "alice", "exp": 9999999999}
        original_jwt = jwt_manager.jwt
        try:
            jwt_manager.jwt = mock_jwt
            token = jwt_manager.generate_token("alice")
            self.assertEqual(token, "eyJfake.jwt.token")

            payload = jwt_manager.verify_token(token)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["user_id"], "alice")
        finally:
            jwt_manager.jwt = original_jwt


class TestAuthenticateLogic(unittest.TestCase):
    """Tests des 6 étapes d'authentification de la route authenticate."""

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        store.init_db(self.temp_db_path)
        self.original_db = store.DB_PATH
        store.DB_PATH = self.temp_db_path

    def tearDown(self):
        store.DB_PATH = self.original_db
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_auth_step1_invalid_nonce(self):
        from routes.authenticate import authenticate, AuthenticateRequest

        req = AuthenticateRequest(
            user_id="user1",
            proof={"a": "b"},
            public_signals=["0xcomm"],
            nonce="invalid-nonce"
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertEqual(res.reason, "Nonce invalide ou expiré")

    def test_auth_step2_user_not_found(self):
        from routes.authenticate import authenticate, AuthenticateRequest

        nonce = "nonce-valid-step2"
        store.save_nonce(nonce, "user_unknown", time.time() + 60)

        req = AuthenticateRequest(
            user_id="user_unknown",
            proof={"a": "b"},
            public_signals=["0xcomm"],
            nonce=nonce
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertEqual(res.reason, "Utilisateur non trouvé ou engagement absent")

    def test_auth_step3_mismatched_commitment(self):
        from routes.authenticate import authenticate, AuthenticateRequest

        user_id = "user_step3"
        nonce = "nonce-step3"
        store.save_commitment(user_id, "0xexpected_commitment")
        store.save_nonce(nonce, user_id, time.time() + 60)

        req = AuthenticateRequest(
            user_id=user_id,
            proof={"a": "b"},
            public_signals=["0xdifferent_commitment"],
            nonce=nonce
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertEqual(res.reason, "L'engagement public ne correspond pas à l'engagement enregistré")

    def test_auth_step4_zkp_failure(self):
        from routes.authenticate import authenticate, AuthenticateRequest

        user_id = "user_step4"
        nonce = "nonce-step4"
        commitment = "0xmatch"
        store.save_commitment(user_id, commitment)
        store.save_nonce(nonce, user_id, time.time() + 60)

        # Désactiver le mock ZKP pour forcer le rejet (fichier introuvable ou preuve invalide)
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)

        req = AuthenticateRequest(
            user_id=user_id,
            proof={"a": "b"},
            public_signals=[commitment],
            nonce=nonce
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertEqual(res.reason, "Échec de la vérification locale de la preuve ZKP")

    def test_auth_step6_success(self):
        from unittest.mock import MagicMock
        from routes.authenticate import authenticate, AuthenticateRequest
        from services import jwt_manager

        user_id = "user_step6"
        nonce = "nonce-step6"
        commitment = "0xcorrect_commitment"
        store.save_commitment(user_id, commitment)
        store.save_nonce(nonce, user_id, time.time() + 60)

        # Activer le mock ZKP
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"

        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "eyJheader.payload.signature"
        original_jwt = jwt_manager.jwt
        jwt_manager.jwt = mock_jwt

        try:
            req = AuthenticateRequest(
                user_id=user_id,
                proof={"pi_a": []},
                public_signals=[commitment],
                nonce=nonce
            )
            res = authenticate(req)
            self.assertTrue(res.authenticated)
            self.assertEqual(res.token, "eyJheader.payload.signature")
            self.assertIsNone(res.reason)
        finally:
            jwt_manager.jwt = original_jwt
            os.environ.pop("MOCK_ZKP_VERIFICATION", None)


class TestRegisterAndNonceRoutes(unittest.TestCase):
    """Tests des routes register et nonce."""

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        store.init_db(self.temp_db_path)
        self.original_db = store.DB_PATH
        store.DB_PATH = self.temp_db_path

    def tearDown(self):
        store.DB_PATH = self.original_db
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_register_success(self):
        from routes.register import register, RegisterRequest

        req = RegisterRequest(user_id="new_user", commitment="0xposeidon_hash")
        res = register(req)
        self.assertTrue(res.success)
        self.assertEqual(res.message, "Engagement enregistré")
        self.assertTrue(store.user_exists("new_user"))

    def test_register_conflict(self):
        from routes.register import register, RegisterRequest
        # En environnement sans FastAPI complet, HTTPException est soit notre mock soit celle de FastAPI
        try:
            from fastapi import HTTPException
        except ImportError:
            HTTPException = Exception

        req = RegisterRequest(user_id="duplicate_user", commitment="0xposeidon_hash")
        register(req)

        with self.assertRaises(Exception):
            register(req)

    def test_get_nonce(self):
        from routes.nonce import get_nonce

        res = get_nonce("test_user_nonce")
        self.assertIsNotNone(res.nonce)
        self.assertEqual(len(res.nonce), 64)  # 32 octets hex = 64 caractères
        self.assertGreater(res.expires_at, time.time())


if __name__ == "__main__":
    unittest.main()
