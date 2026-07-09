import argparse
import json
import os
import sys
import hashlib
import hmac
import secrets

def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)

def provision(username: str, password: str, path: str = "ai_test_auth.json") -> None:
    # Her cagrida uzerine yaz (parola/kullanici degistirilebilsin)
    salt = os.urandom(16)
    hashed_password = _hash(password, salt).hex()
    with open(path, 'w') as f:
        json.dump({
            "username": username,
            "salt": salt.hex(),
            "hash": hashed_password,
            "algo": "scrypt",
            "n": 16384,
            "r": 8,
            "p": 1
        }, f)

def verify(username: str, password: str, path: str = "ai_test_auth.json") -> bool:
    try:
        if not os.path.exists(path):
            return False
        with open(path, 'r') as f:
            data = json.load(f)
        if username != data["username"]:
            return False
        stored_salt = bytes.fromhex(data["salt"])
        stored_hash = bytes.fromhex(data["hash"])
        current_hash = _hash(password, stored_salt)
        return hmac.compare_digest(current_hash, stored_hash)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Password-protected authorization for AI attack-test tool.")
    subparsers = parser.add_subparsers(dest='command')

    set_parser = subparsers.add_parser('set', help="Provision a new user with password or generate one.")
    set_parser.add_argument('--user', required=True, help="Username for the account.")
    set_parser.add_argument('--password', default=None, help="Password for the account (optional).")

    check_parser = subparsers.add_parser('check', help="Verify user credentials.")
    check_parser.add_argument('--user', required=True, help="Username to verify.")
    check_parser.add_argument('--password', required=True, help="Password for verification.")

    args = parser.parse_args()

    if args.command == 'set':
        username = args.user
        password = args.password or secrets.token_urlsafe(12)
        provision(username, password)
        print("USERNAME: " + username)
        print("PASSWORD: " + password)  # tek seferlik goster (paylas); dosyada hash tutulur
        print("STORED  : ai_test_auth.json (salted scrypt; plaintext password not stored)")
    elif args.command == 'check':
        username = args.user
        password = args.password
        if verify(username, password):
            print("OK")
            sys.exit(0)
        else:
            print("FAIL")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
