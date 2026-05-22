import requests
import json

STUDENT_ID = "23P31A05A1"
REPO_URL = "https://github.com/babithaanguluri/-PKI-Based-2FA-Microservice-with-Docker"
API_URL = "https://eajeyq4r3zljoq4rpovy2nthda0vtjqf.lambda-url.ap-south-1.on.aws"

with open("student_public.pem", "r") as f:
    public_key = f.read()

payload = {
    "student_id": STUDENT_ID,
    "github_repo_url": REPO_URL,
    "public_key": public_key
}

print("Sending request...")
response = requests.post(API_URL, json=payload, timeout=20)

print("Response Status:", response.status_code)
print("Response Body:", response.text)

if response.status_code == 200:
    data = response.json()
    encrypted_seed = data.get("encrypted_seed")
    if encrypted_seed:
        with open("encrypted_seed.txt", "w") as f:
            f.write(encrypted_seed)
        print("\nEncrypted seed saved to encrypted_seed.txt")