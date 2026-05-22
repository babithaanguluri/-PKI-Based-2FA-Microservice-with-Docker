from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from app.crypto_utils import load_private_key, decrypt_seed
from app.totp_utils import generate_totp_code, verify_totp_code, get_seconds_remaining

app = FastAPI(title="Secure PKI 2FA Microservice")

SEED_FILE_PATH = "/data/seed.txt"


# -------------------------------
# Request Models
# -------------------------------
class DecryptSeedRequest(BaseModel):
    encrypted_seed: str


class VerifyRequest(BaseModel):
    code: str


# -------------------------------
# Endpoint 0: GET / (Root Health Check)
# -------------------------------
@app.get("/")
def read_root():
    seed_exists = os.path.exists(SEED_FILE_PATH)
    return {
        "status": "healthy",
        "service": "Secure PKI-Based 2FA Microservice",
        "seed_decrypted": seed_exists
    }


# -------------------------------
# Endpoint 1: POST /decrypt-seed
# -------------------------------
@app.post("/decrypt-seed")
def decrypt_seed_endpoint(payload: DecryptSeedRequest):
    encrypted_seed = payload.encrypted_seed

    if not encrypted_seed:
        raise HTTPException(status_code=400, detail="Missing encrypted_seed")

    try:
        private_key = load_private_key()
        hex_seed = decrypt_seed(encrypted_seed, private_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {str(e)}")

    # Ensure /data directory exists (useful when testing locally)
    os.makedirs(os.path.dirname(SEED_FILE_PATH), exist_ok=True)

    # Save hex seed
    try:
        with open(SEED_FILE_PATH, "w") as f:
            f.write(hex_seed)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save seed")

    return {"status": "ok"}


# ------------------------------
# Endpoint 2: GET /generate-2fa
# ------------------------------
@app.get("/generate-2fa")
def generate_2fa():
    # Check seed file exists
    if not os.path.exists(SEED_FILE_PATH):
        raise HTTPException(status_code=400, detail="Seed not decrypted yet")

    # Read hex seed
    try:
        with open(SEED_FILE_PATH, "r") as f:
            hex_seed = f.read().strip()
    except Exception:
        raise HTTPException(status_code=500, detail="Cannot read seed file")

    try:
        code = generate_totp_code(hex_seed)
        valid_for = get_seconds_remaining()
    except Exception:
        raise HTTPException(status_code=500, detail="TOTP generation failed")

    return {
        "code": code,
        "valid_for": valid_for
    }


# ------------------------------
# Endpoint 3: POST /verify-2fa
# ------------------------------
@app.post("/verify-2fa")
def verify_2fa(payload: VerifyRequest):
    if not payload.code:
        raise HTTPException(status_code=400, detail="Missing code")

    # Validate code format (must be 6-digit numeric string)
    if not payload.code.isdigit() or len(payload.code) != 6:
        raise HTTPException(status_code=400, detail="Invalid code format. Code must be a 6-digit numeric string.")

    if not os.path.exists(SEED_FILE_PATH):
        raise HTTPException(status_code=400, detail="Seed not decrypted yet")

    try:
        with open(SEED_FILE_PATH, "r") as f:
            hex_seed = f.read().strip()
    except Exception:
        raise HTTPException(status_code=500, detail="Cannot read seed file")

    is_valid = verify_totp_code(hex_seed, payload.code)

    return {"valid": is_valid}