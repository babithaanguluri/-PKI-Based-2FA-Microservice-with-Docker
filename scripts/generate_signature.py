from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import subprocess

# 1. Get latest commit hash
commit_hash = subprocess.check_output(["git", "log", "-1", "--format=%H"]).decode().strip()
print("="*60)
print("Commit Hash:", commit_hash)
print("="*60)

# 2. Load student private key
with open("student_private.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# 3. Load instructor public key
with open("instructor_public.pem", "rb") as f:
    instructor_pub = serialization.load_pem_public_key(f.read())


# --- Padding Scheme A: PKCS1v1.5 (Standard for GPG/Git/OpenSSL defaults) ---
signature_pkcs = private_key.sign(
    commit_hash.encode("utf-8"),
    padding.PKCS1v15(),
    hashes.SHA256(),
)

encrypted_pkcs = instructor_pub.encrypt(
    signature_pkcs,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )
)
encrypted_pkcs_b64 = base64.b64encode(encrypted_pkcs).decode().strip()


# --- Padding Scheme B: PSS (Probabilistic Signature Scheme) ---
signature_pss = private_key.sign(
    commit_hash.encode("utf-8"),
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    ),
    hashes.SHA256(),
)

encrypted_pss = instructor_pub.encrypt(
    signature_pss,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )
)
encrypted_pss_b64 = base64.b64encode(encrypted_pss).decode().strip()


print("\n[OPTION 1] Encrypted Signature using PKCS#1 v1.5 padding (Recommended):")
print(encrypted_pkcs_b64)

print("\n[OPTION 2] Encrypted Signature using PSS padding:")
print(encrypted_pss_b64)
print("="*60)