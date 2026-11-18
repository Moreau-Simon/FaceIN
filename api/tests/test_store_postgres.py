"""
Tests unitaires et d'intégration pour le backend PostgreSQL du store FaceIn.
Couvre les exigences du PROMPT 3 :
- Pool thread-safe (ThreadedConnectionPool)
- Contrôle de disponibilité (ping)
- Inscription et mise à jour atomique d'engagements
- Unicité et méthode user_exists() indépendante du statut
- Consommation atomique des nonces via DELETE ... RETURNING
- Protection de reset_store contre le TRUNCATE destructeur
- Fermeture propre des connexions (close)
"""

import os
import sys
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


if __name__ == "__main__":
    unittest.main()
