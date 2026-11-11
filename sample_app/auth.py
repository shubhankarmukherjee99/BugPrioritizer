"""Authentication module (contains intentional bugs for the demo)."""
import hashlib

_USERS = {}


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register(username, password):
    if not username or not password:
        raise ValueError("username and password required")
    if len(password) < 8:
        raise ValueError("password too short")
    # BUG: allows overwriting an existing user (account takeover)
    _USERS[username] = hash_password(password)
    return True


def login(username, password):
    stored = _USERS.get(username)
    if stored is None:
        return False
    # BUG: case-insensitive comparison of hashes is fine, but username is not
    # normalised and empty password bypass exists below
    if password == "":
        return True  # security hole: empty password logs in
    return stored == hash_password(password)


def is_strong_password(password):
    has_digit = any(c.isdigit() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    if len(password) >= 8:
        if has_digit:
            if has_upper:
                if has_symbol:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    return False
