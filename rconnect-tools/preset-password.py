#!/usr/bin/env python3
"""Generate RConnect preset-password values (salted hash) for the support build.

Reads the password from STDIN (never argv), makes a random salt, prints:
    RCONNECT_PRESET_PASSWORD=<storage>
    RCONNECT_PRESET_SALT=<salt>
Store both as GitHub Actions secrets of the same names. Python stdlib only.

Algorithm (must match libs/hbb_common/src/config/permanent_password.rs):
  h1      = SHA-256(password_utf8 || salt_utf8)   compute_permanent_password_h1 (l.23-34);
            PERMANENT_PASSWORD_H1_LEN = 32 = whole digest.
  storage = "00" + base64_standard_padded(h1)     HBBS_PRESET_PASSWORD_HASH_PREFIX (l.12),
            decode_preset_password_h1_from_storage (l.134-138) -> decode_password_h1_after_prefix
            (l.59-72; sodiumoxide base64::Variant::Original = RFC 4648 with padding).
  The salt is used as a plain string (its UTF-8 bytes). It MUST be non-empty: with an empty
  salt, preset_permanent_password_storage_is_usable_for_auth (l.124-132) and
  validate_preset_password_storage (src/server/connection.rs:2559) treat `storage` as PLAINTEXT.
Server side: Config::get_effective_permanent_password_salt (config.rs:1556) sends the preset
salt to the peer; peer sends SHA-256(h1 || challenge); verify_h1 (connection.rs:2521) compares.

  --self-test   verify the algorithm against a fixed vector and exit.
"""
import base64
import hashlib
import secrets
import sys


def storage_for(password: str, salt: str) -> str:
    h1 = hashlib.sha256(password.encode("utf-8") + salt.encode("utf-8")).digest()
    return "00" + base64.b64encode(h1).decode("ascii")


def self_test() -> int:
    # Inputs are the ones used by the hbb_common unit tests (permanent_password.rs, "p@ssw0rd"/
    # "salt123"). Expected literal computed independently:
    #   printf 'p@ssw0rdsalt123' | sha256sum | cut -d' ' -f1 | xxd -r -p | base64
    expected = "00tJXMnJwJJKbYZ4XTGfbdbRNVo4aH/rTmq18avAvPzIk="
    got = storage_for("p@ssw0rd", "salt123")
    ok = got == expected and len(base64.b64decode(got[2:])) == 32
    print("self-test:", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    args = sys.argv[1:]
    if args == ["--self-test"]:
        return self_test()
    if args:
        print("usage: preset-password.py [--self-test]  (password on stdin)", file=sys.stderr)
        return 2
    password = sys.stdin.readline().rstrip("\r\n")
    if len(password) < 12:
        print("error: password must be at least 12 characters", file=sys.stderr)
        return 1
    salt = secrets.token_urlsafe(24)  # 32 ASCII chars, non-empty
    print(f"RCONNECT_PRESET_PASSWORD={storage_for(password, salt)}")
    print(f"RCONNECT_PRESET_SALT={salt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
