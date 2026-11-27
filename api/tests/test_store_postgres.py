"""
Tests unitaires et d'intégration pour le backend PostgreSQL du store FaceIn.
Couvre les exigences du stockage persistant :
- Pool thread-safe (ThreadedConnectionPool)
- Contrôle de disponibilité (ping)
- Inscription et mise à jour atomique d'engagements
- Unicité et méthode user_exists() indépendante du statut
- Consommation atomique des nonces via DELETE ... RETURNING
- Protection de reset_store contre le TRUNCATE destructeur
- Fermeture propre des connexions (close)
"""

from concurrent.futures import ThreadPoolExecutor
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services import store


class TestStorePostgresUnit(unittest.TestCase):
    """Tests unitaires du backend PostgresStore avec pool simulé."""

    def setUp(self):
        # Assure un état propre
        store.reset_store()

    def tearDown(self):
        store.reset_store()

    def test_postgres_store_requires_psycopg2(self):
        """Vérifie que PostgresStore lève ImportError si psycopg2 est absent."""
        original_psycopg2 = store.psycopg2
        try:
            store.psycopg2 = None
            with self.assertRaises(ImportError):
                store.PostgresStore()
        finally:
            store.psycopg2 = original_psycopg2

    def test_postgres_store_uses_threaded_pool(self):
        """Vérifie l'instanciation de ThreadedConnectionPool pour le multithreading."""
        mock_psycopg2 = Mock()
        mock_pool = Mock()
        mock_threaded_pool = Mock()
        mock_pool.ThreadedConnectionPool.return_value = mock_threaded_pool

        with patch.object(store, "psycopg2", mock_psycopg2), patch.object(
            store, "pool", mock_pool
        ):
            instance = store.PostgresStore("postgresql://test:test@localhost:5432/testdb")
            mock_pool.ThreadedConnectionPool.assert_called_once_with(
                minconn=2,
                maxconn=20,
                dsn="postgresql://test:test@localhost:5432/testdb",
            )
            self.assertEqual(instance._pool, mock_threaded_pool)

    def test_postgres_store_ping_success(self):
        """Vérifie que ping() renvoie True lorsque la DB répond."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            self.assertTrue(inst.ping())
            mock_cursor.execute.assert_called_with("SELECT 1;")
            mock_pool.putconn.assert_called_with(mock_conn)

    def test_postgres_store_ping_failure(self):
        """Vérifie que ping() renvoie False en cas d'erreur de connexion."""
        mock_pool = Mock()
        mock_pool.getconn.side_effect = RuntimeError("DB down")

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            self.assertFalse(inst.ping())

    def test_postgres_store_close_shuts_down_pool(self):
        """Vérifie que close() ferme toutes les connexions du pool."""
        mock_pool = Mock()

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            inst.close()
            mock_pool.closeall.assert_called_once()
            self.assertIsNone(inst._pool)

    def test_postgres_store_save_engagement_atomic(self):
        """Vérifie que save_engagement effectue un upsert atomique ON CONFLICT."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("00000000-0000-0000-0000-000000000001",)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            inst.save_engagement("alice", "123456789")

            # 3 requêtes exécutées dans la transaction
            calls = mock_cursor.execute.call_args_list
            self.assertEqual(len(calls), 3)

            # 1. Insertion / Upsert utilisateur
            insert_user_sql = calls[0].args[0]
            self.assertIn("ON CONFLICT (nom) DO UPDATE", insert_user_sql)
            self.assertEqual(calls[0].args[1], ("alice",))

            # 2. Révocation des anciens engagements
            revoke_sql = calls[1].args[0]
            self.assertIn("UPDATE engagements_cryptographiques", revoke_sql)

            # 3. Insertion du nouvel engagement actif
            insert_comm_sql = calls[2].args[0]
            self.assertIn("INSERT INTO engagements_cryptographiques", insert_comm_sql)

    def test_postgres_store_user_exists_independent_of_engagement(self):
        """Vérifie que user_exists teste la table utilisateurs directement."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            self.assertTrue(inst.user_exists("alice"))

            sql, params = mock_cursor.execute.call_args.args
            self.assertIn("FROM utilisateurs WHERE nom = %s", sql)
            self.assertEqual(params, ("alice",))

    def test_postgres_store_consume_nonce_atomic_delete_returning(self):
        """Vérifie la consommation atomique par DELETE ... RETURNING en 1 seule requête."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("my-nonce",)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(store, "psycopg2", Mock()), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            result = inst.consume_nonce("nonce-123", user_id="bob", now=1000.0)

            self.assertTrue(result)
            self.assertEqual(mock_cursor.execute.call_count, 1)

            sql, params = mock_cursor.execute.call_args.args
            self.assertIn("DELETE FROM nonces", sql)
            self.assertIn("RETURNING nonce", sql)
            self.assertEqual(params[0], "nonce-123")
            self.assertEqual(params[1], "bob")

    def test_postgres_store_destructive_truncate_blocked_without_env_flag(self):
        """Vérifie que clear() et reset_store() refusent le TRUNCATE par défaut."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.dict(os.environ, {"ALLOW_DESTRUCTIVE_STORE_RESET": "false"}), patch.object(
            store, "psycopg2", Mock()
        ), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            inst.clear()
            # Aucune requête TRUNCATE ne doit avoir été exécutée
            mock_cursor.execute.assert_not_called()

    def test_postgres_store_destructive_truncate_allowed_with_flag(self):
        """Vérifie que clear() autorise le TRUNCATE si ALLOW_DESTRUCTIVE_STORE_RESET=true."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_pool = Mock()
        mock_pool.getconn.return_value = mock_conn

        with patch.dict(os.environ, {"ALLOW_DESTRUCTIVE_STORE_RESET": "true"}), patch.object(
            store, "psycopg2", Mock()
        ), patch.object(
            store, "pool", Mock(ThreadedConnectionPool=Mock(return_value=mock_pool))
        ):
            inst = store.PostgresStore()
            inst.clear()
            mock_cursor.execute.assert_called_once()
            self.assertIn("TRUNCATE TABLE", mock_cursor.execute.call_args.args[0])


@unittest.skipUnless(
    os.getenv("TEST_POSTGRES_URL"),
    "TEST_POSTGRES_URL non définie (tests d'intégration PostgreSQL isolés ignorés en local)",
)
class TestStorePostgresIntegration(unittest.TestCase):
    """Tests d'intégration sur une base PostgreSQL de test isolée."""

    def setUp(self):
        self.db_url = os.environ["TEST_POSTGRES_URL"]
        self.pg = store.PostgresStore(database_url=self.db_url)
        with patch.dict(os.environ, {"ALLOW_DESTRUCTIVE_STORE_RESET": "true"}):
            self.pg.clear()

    def tearDown(self):
        with patch.dict(os.environ, {"ALLOW_DESTRUCTIVE_STORE_RESET": "true"}):
            self.pg.clear()
        self.pg.close()

    def test_postgres_roundtrip_engagement_nonce_revocation_jwt(self):
        self.assertTrue(self.pg.ping())
        self.pg.save_engagement("pg_alice", "123456789")
        self.assertEqual(self.pg.get_engagement("pg_alice")["commitment"], "123456789")

        # Nonce atomique à usage unique
        self.pg.save_nonce("pg_nonce_1", "pg_alice", time.time() + 60.0)
        self.assertTrue(self.pg.consume_nonce("pg_nonce_1", "pg_alice"))
        self.assertFalse(self.pg.consume_nonce("pg_nonce_1", "pg_alice"))

        # Révocation JTI et autorisation par service
        self.pg.save_revoked_jti("pg-jti-1", time.time() + 120.0)
        self.assertTrue(self.pg.is_jti_revoked("pg-jti-1"))

        self.pg.set_service_authorization("pg_alice", "facein-web", "revoque")
        self.assertFalse(self.pg.is_service_authorized("pg_alice", "facein-web"))

    def test_postgres_creation_utilisateur_en_double_refusee(self):
        self.assertTrue(self.pg.create_user_with_engagement("pg_bob", "111"))
        self.assertFalse(self.pg.create_user_with_engagement("pg_bob", "222"))
        # L'engagement initial n'est pas écrasé par la tentative en double
        self.assertEqual(self.pg.get_engagement("pg_bob")["commitment"], "111")

    def test_postgres_inscriptions_concurrentes_meme_utilisateur(self):
        nb = 10
        barriere = threading.Barrier(nb)

        def inscrire(idx):
            barriere.wait(timeout=10)
            return self.pg.create_user_with_engagement("pg_race", str(9000 + idx))

        with ThreadPoolExecutor(max_workers=nb) as pool:
            resultats = list(pool.map(inscrire, range(nb)))

        self.assertEqual(resultats.count(True), 1)
        gagnant = str(9000 + resultats.index(True))
        self.assertEqual(self.pg.get_engagement("pg_race")["commitment"], gagnant)
        with self.pg.get_cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM engagements_cryptographiques ec
                JOIN utilisateurs u ON u.id = ec.utilisateur_id WHERE u.nom = %s;
                """,
                ("pg_race",),
            )
            self.assertEqual(cur.fetchone()[0], 1)

    def test_postgres_mise_a_jour_engagement_un_seul_actif(self):
        self.pg.save_engagement("pg_carol", "1")
        self.pg.save_engagement("pg_carol", "2")
        self.assertEqual(self.pg.get_engagement("pg_carol")["commitment"], "2")
        with self.pg.get_cursor() as cur:
            cur.execute(
                """
                SELECT ec.statut, count(*) FROM engagements_cryptographiques ec
                JOIN utilisateurs u ON u.id = ec.utilisateur_id
                WHERE u.nom = %s GROUP BY ec.statut;
                """,
                ("pg_carol",),
            )
            statuts = dict(cur.fetchall())
        self.assertEqual(statuts, {"actif": 1, "revoque": 1})

    def test_postgres_consommations_simultanees_nonce_une_seule_reussit(self):
        self.pg.save_engagement("pg_dave", "42")
        self.pg.save_nonce("pg_nonce_conc", "pg_dave", time.time() + 60.0)
        nb = 16
        barriere = threading.Barrier(nb)

        def consommer(_):
            barriere.wait(timeout=10)
            return self.pg.consume_nonce("pg_nonce_conc", "pg_dave")

        with ThreadPoolExecutor(max_workers=nb) as pool:
            resultats = list(pool.map(consommer, range(nb)))
        self.assertEqual(resultats.count(True), 1)

    def test_postgres_nonce_mauvais_utilisateur_non_consomme(self):
        self.pg.save_engagement("pg_erin", "42")
        self.pg.save_nonce("pg_nonce_owner", "pg_erin", time.time() + 60.0)
        self.assertFalse(self.pg.consume_nonce("pg_nonce_owner", "pg_mallory"))
        # Le nonce du vrai propriétaire reste utilisable une seule fois
        self.assertTrue(self.pg.consume_nonce("pg_nonce_owner", "pg_erin"))
        self.assertFalse(self.pg.consume_nonce("pg_nonce_owner", "pg_erin"))

    def test_postgres_nonce_expire_refuse(self):
        self.pg.save_engagement("pg_frank", "42")
        self.pg.save_nonce("pg_nonce_exp", "pg_frank", time.time() - 1.0)
        self.assertFalse(self.pg.consume_nonce("pg_nonce_exp", "pg_frank"))

    def test_postgres_persistance_apres_redemarrage_du_pool(self):
        self.pg.save_engagement("pg_gina", "777")
        self.pg.save_revoked_jti("pg-jti-persist", time.time() + 120.0)
        self.pg.close()
        # Pool fermé : la disponibilité est signalée négative, jamais simulée
        self.assertFalse(self.pg.ping())
        with self.assertRaises(RuntimeError):
            self.pg.get_engagement("pg_gina")

        # Nouvelle instance = redémarrage de l'API
        self.pg = store.PostgresStore(database_url=self.db_url)
        self.assertTrue(self.pg.ping())
        self.assertEqual(self.pg.get_engagement("pg_gina")["commitment"], "777")
        self.assertTrue(self.pg.is_jti_revoked("pg-jti-persist"))


if __name__ == "__main__":
    unittest.main()
