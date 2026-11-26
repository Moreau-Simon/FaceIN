"""
Modèles Pydantic et règles de validation strictes pour l'API Gateway FaceIn.
Garantit l'intégrité des entrées, la conformité cryptographique des formats
et l'uniformité des réponses exposées au frontend.
"""

import re
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator

# Ordre du corps fini BN254 (snarkjs / alt_bn128)
BN254_FIELD_ORDER = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)

USER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def validate_user_id_format(value: str) -> str:
    """Valide la taille et les caractères d'un identifiant utilisateur."""
    cleaned = value.strip()
    if not USER_ID_REGEX.match(cleaned):
        raise ValueError(
            "L'identifiant utilisateur doit contenir entre 3 et 64 caractères "
            "alphanumériques, tirets ou underscores uniquement."
        )
    return cleaned


def validate_bn254_element(value: str, field_name: str = "commitment") -> str:
    """Valide qu'une valeur représente un élément strict du corps fini BN254."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Le champ '{field_name}' ne peut pas être vide.")

    try:
        if cleaned.startswith(("0x", "0X")):
            numeric_val = int(cleaned, 16)
        else:
            numeric_val = int(cleaned, 10)
    except ValueError:
        raise ValueError(
            f"Le champ '{field_name}' doit être une représentation décimale ou hexadécimale valide."
        )

    if not (0 <= numeric_val < BN254_FIELD_ORDER):
        raise ValueError(
            f"Le champ '{field_name}' est hors des limites du corps fini BN254 [0, {BN254_FIELD_ORDER - 1}]."
        )

    return cleaned


# =====================================================================
# Modèles d'enregistrement (Register)
# =====================================================================
class RegisterRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur (3 à 64 caractères)")
    commitment: str = Field(
        ...,
        description="Empreinte Poseidon de référence dans le corps fini BN254",
    )

    @field_validator("user_id")
    @classmethod
    def check_user_id(cls, v: str) -> str:
        return validate_user_id_format(v)

    @field_validator("commitment")
    @classmethod
    def check_commitment(cls, v: str) -> str:
        return validate_bn254_element(v, "commitment")


class RegisterResponse(BaseModel):
    success: bool = Field(True, description="Statut de l'opération")
    message: str = Field(..., description="Message informatif pour le client")


# =====================================================================
# Modèles de Nonce
# =====================================================================
class NonceResponse(BaseModel):
    success: bool = Field(True, description="Statut de l'opération")
    nonce: str = Field(..., description="Défi hexadécimal aléatoire anti-rejeu de 256 bits (64 hex chars)")
    expires_at: int = Field(..., description="Timestamp Unix d'expiration")
    defis: List[str] = Field(
        default_factory=list,
        description="Liste ordonnée des défis de vie à exécuter",
    )


# =====================================================================
# Modèles d'authentification (Authenticate)
# =====================================================================
class AuthenticateRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur")
    proof: dict[str, Any] = Field(
        ...,
        description="Preuve Groth16 générée côté client contenant pi_a, pi_b, pi_c",
    )
    public_signals: List[str] = Field(
        ...,
        min_length=1,
        description="Signaux publics du circuit : [0]=engagement, [1]=seuil (optionnel)",
    )
    nonce: str = Field(..., description="Nonce cryptographique reçu lors de l'étape de défi")

    @field_validator("user_id")
    @classmethod
    def check_user_id(cls, v: str) -> str:
        return validate_user_id_format(v)

    @field_validator("nonce")
    @classmethod
    def check_nonce(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.match(r"^[0-9a-fA-F]{32,64}$", cleaned):
            raise ValueError("Le nonce doit être une chaîne hexadécimale valide de 32 à 64 caractères.")
        return cleaned

    @field_validator("proof")
    @classmethod
    def check_proof_structure(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("La preuve Groth16 doit être un objet JSON valide.")
        for key in ("pi_a", "pi_b", "pi_c"):
            if key not in v:
                raise ValueError(f"La preuve Groth16 est incomplète : champ '{key}' manquant.")
        return v

    @field_validator("public_signals")
    @classmethod
    def check_public_signals(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("La liste des signaux publics ne peut pas être vide.")
        for idx, signal in enumerate(v):
            validate_bn254_element(str(signal), f"public_signals[{idx}]")
        return [str(s).strip() for s in v]


class AuthenticateResponse(BaseModel):
    success: bool = Field(..., description="Succès ou échec global de la demande")
    authenticated: bool = Field(..., description="Indique si la preuve et les vérifications sont validées")
    token: Optional[str] = Field(None, description="Jeton JWT d'accès en cas de succès")
    reason: Optional[str] = Field(None, description="Raison en cas de refus (compatibilité backend)")
    raison_refus: Optional[str] = Field(None, description="Raison en cas de refus (compatibilité frontend)")
    message: str = Field(..., description="Message informatif")


# =====================================================================
# Modèles d'erreur et de santé
# =====================================================================
class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Toujours False pour une erreur")
    code: str = Field(..., description="Code d'erreur applicatif standardisé")
    message: str = Field(..., description="Message d'erreur sécurisé pour l'utilisateur")
    detail: Optional[str] = Field(None, description="Détails complémentaires d'erreur de validation")


class HealthResponse(BaseModel):
    statut: str = Field("en_ligne", description="Statut global du service (en_ligne, degrade, critique)")
    service: str = Field("FaceIn API Gateway", description="Nom du service")
    version: str = Field("1.0.0", description="Version du service")
    processus: str = Field("ok", description="État du processus API")
    stockage: str = Field(..., description="Type de backend de persistance actif (memory ou postgres)")
    stockage_ok: bool = Field(True, description="Disponibilité du backend de stockage")
    zkp_ok: bool = Field(True, description="Disponibilité du vérificateur ZKP (clé et moteur)")
    noeuds_configures: int = Field(..., description="Nombre de noeuds de vérification configurés")
    noeuds_disponibles: int = Field(0, description="Nombre de noeuds joignables")
    quorum_atteint: bool = Field(False, description="Indique si le quorum minimal (2/3) est disponible")
