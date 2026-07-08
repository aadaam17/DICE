import pytest

from dice.core.secrets import SecretStore


def test_secret_store_round_trips_private_key(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("DICE_SECRET_PASSWORD", "test-password")
    store = SecretStore(tmp_path)
    private_key = "0x" + "1" * 64

    ref = store.store_private_key("job-0001", "Wallet", private_key)

    assert ref == "secret://wallets/job-0001"
    assert private_key not in (tmp_path / "job-0001.json").read_text(encoding="utf-8")
    assert store.load_private_key(ref) == private_key


def test_secret_store_lists_named_wallets(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("DICE_SECRET_PASSWORD", "test-password")
    store = SecretStore(tmp_path)
    private_key = "0x" + "2" * 64

    ref = store.store_wallet("Base Sweeper", "Base Sweeper", "0xabc", private_key)
    wallets = store.list_wallets()

    assert ref == "secret://wallets/BaseSweeper"
    assert wallets[0].ref == ref
    assert wallets[0].label == "Base Sweeper"
    assert wallets[0].address == "0xabc"
    assert store.load_private_key(ref) == private_key


def test_secret_store_requires_master_password(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.delenv("DICE_SECRET_PASSWORD", raising=False)
    store = SecretStore(tmp_path)

    with pytest.raises(RuntimeError, match="DICE_SECRET_PASSWORD"):
        store.store_private_key("job-0001", "Wallet", "0x" + "1" * 64)
