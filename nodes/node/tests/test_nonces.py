"""Tests du magasin de nonces en mémoire."""

from concurrent.futures import ThreadPoolExecutor

from verification.nonces import NonceStore


def test_nonce_est_a_usage_unique():
    store = NonceStore()
    nonce, _ = store.emettre("user-1")

    assert store.consommer("user-1", nonce) is True
    assert store.consommer("user-1", nonce) is False


def test_nonce_expire_est_refuse_avec_une_horloge_factice():
    maintenant = [100.0]
    store = NonceStore(duree_s=5, horloge=lambda: maintenant[0])
    nonce, expiration_ms = store.emettre("user-1")

    assert expiration_ms == 105_000
    maintenant[0] = 105.001

    assert store.consommer("user-1", nonce) is False


def test_nonce_est_refuse_et_consomme_pour_un_mauvais_utilisateur():
    store = NonceStore()
    nonce, _ = store.emettre("user-1")

    assert store.consommer("user-2", nonce) is False
    assert store.consommer("user-1", nonce) is False


def test_nonce_inconnu_est_refuse():
    store = NonceStore()

    assert store.consommer("user-1", "nonce-inconnu") is False


def test_un_nonce_ne_peut_etre_consomme_qu_une_fois_en_concurrence():
    store = NonceStore()
    nonce, _ = store.emettre("user-1")

    with ThreadPoolExecutor(max_workers=16) as executor:
        resultats = list(
            executor.map(
                lambda _: store.consommer("user-1", nonce),
                range(64),
            )
        )

    assert sum(resultats) == 1
