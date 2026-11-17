-- ============================================================
-- FaceIN — Initialisation de la Base de Données (PostgreSQL 16)
-- Schéma complet : Blocs A, B, C, D, E + Table de Nonces ZKP
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------
-- BLOC A : L'Identité Privacy by Design
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS utilisateurs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom              VARCHAR(100) NOT NULL,
    date_inscription TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engagements_cryptographiques (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id  UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    valeur          TEXT NOT NULL,
    algorithme      VARCHAR(50) NOT NULL,
    statut          VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'revoque')),
    date_creation   TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_revocation TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_un_seul_engagement_actif
    ON engagements_cryptographiques (utilisateur_id)
    WHERE statut = 'actif';

CREATE INDEX IF NOT EXISTS idx_engagements_utilisateur 
    ON engagements_cryptographiques(utilisateur_id);

-- ------------------------------------------------------------
-- BLOC B : Le Registre Incorruptible
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_audit (
    id              BIGSERIAL PRIMARY KEY,
    hash_precedent  CHAR(64) NOT NULL,
    hash_courant    CHAR(64) NOT NULL UNIQUE,
    action          VARCHAR(50) NOT NULL,
    utilisateur_id  UUID REFERENCES utilisateurs(id),
    noeud           VARCHAR(50) NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    signature       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_journal_utilisateur ON journal_audit(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal_audit(timestamp);

-- ------------------------------------------------------------
-- BLOC D : Réseau Distribué et Résilience
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS noeuds_verification (
    id                VARCHAR(50) PRIMARY KEY,
    adresse           VARCHAR(255) NOT NULL,
    statut            VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'hors_ligne')),
    derniere_activite TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS racines_merkle (
    id          BIGSERIAL PRIMARY KEY,
    noeud_id    VARCHAR(50) NOT NULL REFERENCES noeuds_verification(id),
    racine_hash CHAR(64) NOT NULL,
    calculee_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    nb_feuilles INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_racines_noeud_date 
    ON racines_merkle(noeud_id, calculee_le DESC);

CREATE TABLE IF NOT EXISTS historique_engagements (
    id             BIGSERIAL PRIMARY KEY,
    utilisateur_id UUID NOT NULL REFERENCES utilisateurs(id),
    engagement_id  UUID NOT NULL REFERENCES engagements_cryptographiques(id),
    action         VARCHAR(20) NOT NULL CHECK (action IN ('creation', 'revocation')),
    raison         TEXT,
    date_action    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS listes_revocation (
    id              BIGSERIAL PRIMARY KEY,
    engagement_id   UUID NOT NULL REFERENCES engagements_cryptographiques(id),
    date_revocation TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS propagation_revocation (
    revocation_id    BIGINT NOT NULL REFERENCES listes_revocation(id),
    noeud_id         VARCHAR(50) NOT NULL REFERENCES noeuds_verification(id),
    statut           VARCHAR(20) NOT NULL DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'propagee')),
    date_propagation TIMESTAMPTZ,
    PRIMARY KEY (revocation_id, noeud_id)
);

-- ------------------------------------------------------------
-- BLOC C : Exploitation et Détection d'Anomalies
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appareils_connus (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id     UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    empreinte_appareil VARCHAR(255) NOT NULL,
    premiere_connexion TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(utilisateur_id, empreinte_appareil)
);

CREATE TABLE IF NOT EXISTS sessions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    ip             INET NOT NULL,
    geoloc         VARCHAR(100),
    horodatage     TIMESTAMPTZ NOT NULL DEFAULT now(),
    appareil_id    UUID REFERENCES appareils_connus(id),
    noeud_utilise  VARCHAR(50) NOT NULL REFERENCES noeuds_verification(id),
    score_anomalie DECIMAL(5,2) NOT NULL DEFAULT 0.00
);

CREATE INDEX IF NOT EXISTS idx_sessions_utilisateur 
    ON sessions(utilisateur_id, horodatage DESC);

CREATE TABLE IF NOT EXISTS patterns_utilisateur (
    utilisateur_id       UUID PRIMARY KEY REFERENCES utilisateurs(id) ON DELETE CASCADE,
    plages_horaires      JSONB NOT NULL DEFAULT '{}'::jsonb,
    zones_geographiques  JSONB NOT NULL DEFAULT '{}'::jsonb,
    derniere_mise_a_jour TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- BLOC E : Cloisonnement Multi-Service
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS services (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom                 VARCHAR(100) NOT NULL UNIQUE,
    cle_publique        TEXT NOT NULL,
    date_enregistrement TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autorisations_service (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id    UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    service_id        UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    statut            VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'revoque')),
    date_autorisation TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(utilisateur_id, service_id)
);

CREATE TABLE IF NOT EXISTS tokens_par_service (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    autorisation_id UUID NOT NULL REFERENCES autorisations_service(id) ON DELETE CASCADE,
    token_derive    TEXT NOT NULL UNIQUE,
    date_creation   TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_expiration TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tokens_expiration 
    ON tokens_par_service(date_expiration);

-- ------------------------------------------------------------
-- Sécurité ZKP : Table des Nonces anti-rejeu (Gateway API)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nonces (
    nonce      VARCHAR(255) PRIMARY KEY,
    user_id    VARCHAR(255) NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);