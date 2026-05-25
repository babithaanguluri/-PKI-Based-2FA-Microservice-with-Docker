# PKI-Based 2FA Microservice

A secure, containerized **Two-Factor Authentication (2FA) microservice** built with FastAPI and Docker. It leverages **Public Key Infrastructure (PKI)** for secure seed delivery and generates **TOTP (Time-based One-Time Password)** codes following the RFC 6238 standard.

---

## Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Getting Started](#-getting-started)
- [API Endpoints](#-api-endpoints)
- [Scripts](#-scripts)
- [Cron Job](#-cron-job)
- [Security Design](#-security-design)
- [Tech Stack](#-tech-stack)

---

## Overview

This microservice provides a complete PKI-secured 2FA workflow:

1. The instructor encrypts a **TOTP seed** using the student's RSA public key.
2. The student sends the encrypted seed to the `/decrypt-seed` endpoint.
3. The service **decrypts** it using the student's RSA private key (RSA-OAEP / SHA-256).
4. The decrypted seed is stored securely and used to **generate and verify** 6-digit TOTP codes.
5. A **cron job** inside the container logs the current TOTP code every minute.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Docker Container                    │
│                                                      │
│  ┌─────────────┐       ┌───────────────────────┐    │
│  │  Cron Job   │──────▶│  generate_totp.py     │    │
│  │ (every min) │       │  logs → /cron/        │    │
│  └─────────────┘       └───────────────────────┘    │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │            FastAPI Application                │  │
│  │                                               │  │
│  │  GET  /              → Health Check           │  │
│  │  POST /decrypt-seed  → RSA Decrypt + Store    │  │
│  │  GET  /generate-2fa  → TOTP Code Generation   │  │
│  │  POST /verify-2fa    → TOTP Code Verification │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  Persistent Volumes: /data (seed) · /cron (logs)    │
└─────────────────────────────────────────────────────┘
         ▲ Port 8080
         │
   External Requests
```

---

## Project Structure

```
pki-2fa-microservice/
│
├── app/
│   ├── __init__.py           # Package initializer
│   ├── main.py               # FastAPI app & all API endpoints
│   ├── crypto_utils.py       # RSA key loading & OAEP decryption
│   └── totp_utils.py         # TOTP generation & verification (pyotp)
│
├── scripts/
│   ├── request_seed.py       # Request encrypted seed from instructor API
│   ├── generate_totp.py      # Standalone TOTP code generator (used by cron)
│   ├── log_2fa_cron.py       # Cron logging script (writes to /cron/last_code.txt)
│   └── generate_signature.py # RSA commit signing (PKCS1v15 & PSS) for submission
│
├── cron/
│   └── 2fa-cron              # Crontab file (runs every minute)
│
├── data/                     # Runtime directory — seed.txt stored here (Docker volume)
│
├── Dockerfile                # Multi-stage Docker build (builder + runtime)
├── docker-compose.yml        # Docker Compose with persistent volumes
├── requirements.txt          # Python dependencies
│
├── student_private.pem       #  RSA private key (DO NOT SHARE)
├── student_public.pem        #  RSA public key (shared with instructor)
├── instructor_public.pem     #  Instructor's RSA public key (for signature encryption)
└── encrypted_seed.txt        # Encrypted seed received from instructor
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 20.10+ |
| Docker Compose | v2+ |
| Python | 3.11+ (for local scripts) |

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/babithaanguluri/-PKI-Based-2FA-Microservice-with-Docker.git
cd pki-2fa-microservice
```

### 2. Ensure RSA Keys Are in Place

```
student_private.pem       ← your RSA private key
student_public.pem        ← your RSA public key
instructor_public.pem     ← provided by instructor
```

 **Never commit `student_private.pem` to a public repository.**

### 3. Request the Encrypted Seed

```bash
python scripts/request_seed.py
```

This submits your student ID, GitHub repo URL, and public key to the instructor's API. The encrypted seed is saved to `encrypted_seed.txt`.

### 4. Build & Start the Container

```bash
docker-compose up --build
```

The service will be available at **http://localhost:8080**.

### 5. Decrypt the Seed

```bash
curl -X POST http://localhost:8080/decrypt-seed \
  -H "Content-Type: application/json" \
  -d "{\"encrypted_seed\": \"$(cat encrypted_seed.txt)\"}"
```

Expected response:
```json
{ "status": "ok" }
```

### 6. Generate a TOTP Code

```bash
curl http://localhost:8080/generate-2fa
```

Expected response:
```json
{ "code": "482931", "valid_for": 17 }
```

### 7. Verify a TOTP Code

```bash
curl -X POST http://localhost:8080/verify-2fa \
  -H "Content-Type: application/json" \
  -d '{"code": "482931"}'
```

Expected response:
```json
{ "valid": true }
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — returns service status and seed availability |
| `POST` | `/decrypt-seed` | Decrypts and stores the RSA-encrypted TOTP seed |
| `GET` | `/generate-2fa` | Returns the current 6-digit TOTP code and seconds remaining |
| `POST` | `/verify-2fa` | Verifies a submitted 6-digit TOTP code (±1 window allowed) |

### Request & Response Examples

#### `GET /`
```json
{
  "status": "healthy",
  "service": "Secure PKI-Based 2FA Microservice",
  "seed_decrypted": true
}
```

#### `POST /decrypt-seed`
**Request Body:**
```json
{ "encrypted_seed": "<base64-encoded ciphertext>" }
```
**Response:**
```json
{ "status": "ok" }
```

#### `GET /generate-2fa`
```json
{ "code": "837291", "valid_for": 24 }
```

#### `POST /verify-2fa`
**Request Body:**
```json
{ "code": "837291" }
```
**Response:**
```json
{ "valid": true }
```

---

## Scripts

### `scripts/request_seed.py`
Sends a POST request to the instructor's Lambda API with the student ID, GitHub repo URL, and RSA public key. Saves the returned `encrypted_seed` to `encrypted_seed.txt`.

```bash
python scripts/request_seed.py
```

### `scripts/generate_totp.py`
Standalone script that reads the decrypted seed from `/data/seed.txt` and prints the current TOTP code with a UTC timestamp. Used internally by the cron job.

```bash
python scripts/generate_totp.py
```

### `scripts/log_2fa_cron.py`
Similar to `generate_totp.py` but appends each code to `/cron/last_code.txt` for persistent audit logging.

```bash
python scripts/log_2fa_cron.py
```

### `scripts/generate_signature.py`
Signs the latest Git commit hash with the student's RSA private key and encrypts the signature using the instructor's RSA public key. Outputs two options:

- **PKCS#1 v1.5** (recommended for most standard verifications)
- **PSS** (Probabilistic Signature Scheme — stronger, randomized)

```bash
python scripts/generate_signature.py
```

---

## Cron Job

The file `cron/2fa-cron` schedules the TOTP generation script to run **every minute** inside the container:

```
* * * * * root /usr/local/bin/python /app/scripts/generate_totp.py >> /cron/last_code.txt 2>&1
```

To view the cron output from a running container:

```bash
docker exec -it pki_2fa_app cat /cron/last_code.txt
```

---

## Security Design

| Component | Details |
|-----------|---------|
| **Key Algorithm** | RSA-2048 |
| **Seed Encryption** | RSA-OAEP with SHA-256 + MGF1(SHA-256) |
| **Seed Format** | 64-character lowercase hexadecimal string |
| **TOTP Algorithm** | HMAC-SHA1, 6 digits, 30-second window |
| **TOTP Tolerance** | ±1 window (allows for up to 30s clock skew) |
| **Private Key Storage** | Mounted as a read-only Docker volume; never hardcoded |
| **Commit Signing** | RSA PKCS#1 v1.5 or PSS, then encrypted with instructor public key |

### Seed Validation
- Must be exactly **64 characters**
- Must match the pattern `[0-9a-f]{64}` (lowercase hex only)

### Code Validation
- Must be exactly **6 digits** (`[0-9]{6}`)
- Numeric string format enforced before TOTP verification

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **ASGI Server** | Uvicorn |
| **Cryptography** | [cryptography](https://cryptography.io/) (RSA-OAEP) |
| **TOTP** | [pyotp](https://github.com/pyauth/pyotp) (RFC 6238) |
| **Containerization** | Docker (multi-stage build) + Docker Compose |
| **Scheduling** | Linux cron daemon |
| **Language** | Python 3.11 |

---

## License

This project was developed as part of an academic assignment in secure systems and PKI infrastructure.

---

*Student ID: 23P31A05A1*
