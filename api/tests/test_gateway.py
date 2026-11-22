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
    """Tests du module de vérification ZKP."""

    def test_zkp_mock_mode(self):
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"
        try:
            result = zkp_verifier.verify_proof(
                proof={"pi_a": []},
                public_signals=["123", "1000"],
            )
            self.assertTrue(result)
        finally:
            os.environ.pop("MOCK_ZKP_VERIFICATION", None)

    def test_missing_vk_returns_false(self):
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)
        result = zkp_verifier.verify_proof(
            proof={"pi_a": []},
            public_signals=["123"],
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
        async def arreter_api():
            async with api_main.lifespan(api_main.app):
                pass

        channel = Mock()
        mock_grpc = grpc_bridge.grpc or Mock()
        mock_grpc.insecure_channel = Mock(return_value=channel)
        mock_grpc.ssl_channel_credentials = Mock()
        mock_grpc.secure_channel = Mock(return_value=channel)

        with patch.dict(os.environ, {"TLS_ENABLED": "false"}), patch.object(
            grpc_bridge, "grpc", mock_grpc
        ):
            grpc_bridge._creer_canal("unused-target:50051")
            asyncio.run(arreter_api())

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
                grpc_bridge, "verification_pb2", SimpleNamespace(DemandeVerification=Mock(return_value=Mock())),
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


class TestJwtManager(unittest.TestCase):
    """Tests pour le gestionnaire de tokens JWT."""

    def test_jwt_generation_and_verification_mocked(self):
        from services import jwt_manager

        mock_jwt = Mock()
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
    """Tests du flux d'authentification biométrique ZKP."""

    def setUp(self):
        store.reset_store()
        self.storage = store.get_store()
        rate_limiter.reset_rate_limiter()
        self.valid_nonce = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def tearDown(self):
        store.reset_store()
        rate_limiter.reset_rate_limiter()

    def test_auth_step1_malformed_nonce_rejected(self):
        from routes.authenticate import authenticate

        # Nonce trop court (32 chars au lieu de 64 chars / 256 bits)
        req = AuthenticateRequest(
            user_id="user1",
            proof={"pi_a": [], "pi_b": [], "pi_c": []},
            public_signals=["123456789"],
            nonce="0123456789abcdef0123456789abcdef",
        )
        res = authenticate(req)
        self.assertFalse(res.authenticated)
        self.assertFalse(res.success)
        self.assertEqual(res.reason, "Nonce malformé (attendu : 64 caractères hexadécimaux)")
        self.assertEqual(res.raison_refus, "Nonce malformé")

    def test_auth_step2_zkp_failure(self):
        from routes.authenticate import authenticate

        user_id = "user_step2"
        commitment = "123456789"

        # Désactiver le mock ZKP pour forcer le rejet (fichier introuvable ou preuve invalide)
        os.environ.pop("MOCK_ZKP_VERIFICATION", None)

        req = AuthenticateRequest(
            user_id=user_id,
            proof={"pi_a": [], "pi_b": [], "pi_c": []},
            public_signals=[commitment],
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
                proof={"pi_a": [], "pi_b": [], "pi_c": []},
                public_signals=[commitment],
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

        # Activer le mock ZKP
        os.environ["MOCK_ZKP_VERIFICATION"] = "true"

        mock_jwt = Mock()
        mock_jwt.encode.return_value = "eyJheader.payload.signature"
        original_jwt = jwt_manager.jwt
        jwt_manager.jwt = mock_jwt

        try:
            req = AuthenticateRequest(
                user_id=user_id,
                proof={"pi_a": [], "pi_b": [], "pi_c": []},
                public_signals=[commitment],
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
            proof={"pi_a": [], "pi_b": [], "pi_c": []},
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
