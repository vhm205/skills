#!/usr/bin/env python3
"""Private behavioral oracle. Invoked only by the parent eval runner."""
import importlib.util
from pathlib import Path
import sys


def main():
    root = Path(sys.argv[1])
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location("candidate", root / "app/auth.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for local in ("alice", "bob", "new.user_42", "MixedCase", "dash-name"):
            for domain in ("example.com", "sub.example.org"):
                plain = f"{local}@{domain}"
                for suffix in ("", "+news", "+a+b", "+"):
                    email = f"{local}{suffix}@{domain}"
                    assert module.normalize_email(email) == plain, (email, plain)
        assert module.find_user("alice+news@example.com")["id"] == 1
        assert module.find_user("bob+new+tags@example.com")["id"] == 2
        module.USERS["oracle-user@example.org"] = {"id": 987, "name": "Oracle"}
        assert module.find_user("oracle-user+tag@example.org")["id"] == 987
    except Exception as exc:
        print("ORACLE_FAIL", type(exc).__name__, str(exc))
        return 1
    print("ORACLE_PASS: normalization and lookup invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
