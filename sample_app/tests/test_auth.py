import pytest
from sample_app import auth


@pytest.fixture(autouse=True)
def clean_users():
    auth._USERS.clear()
    yield
    auth._USERS.clear()


def test_register_and_login():
    auth.register("alice", "Secret#123")
    assert auth.login("alice", "Secret#123")


def test_wrong_password_rejected():
    auth.register("bob", "Secret#123")
    assert not auth.login("bob", "wrongpass")


def test_empty_password_rejected():
    auth.register("carol", "Secret#123")
    assert not auth.login("carol", ""), "security: empty password must not log in"


def test_duplicate_registration_blocked():
    auth.register("dave", "Secret#123")
    with pytest.raises(ValueError):
        auth.register("dave", "Hacker#999")


def test_short_password():
    with pytest.raises(ValueError):
        auth.register("eve", "abc")


def test_strong_password():
    assert auth.is_strong_password("Abcdef1!")
    assert not auth.is_strong_password("abcdefgh")
