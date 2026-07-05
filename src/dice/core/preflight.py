from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from dice.adapters.factory import create_adapter
from dice.adapters.mock import MockChainAdapter
from dice.core.models import JobConfig
from dice.core.registry import load_builtin_plugins, registry
from dice.core.secrets import SecretStore
from dice.core.validation import validate_job
from dice.execution.signer import PrivateKeySigner
from dice.execution.simulation import TransactionSimulator


class PreflightStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    status: PreflightStatus
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status.value, "message": self.message}


@dataclass(frozen=True, slots=True)
class PreflightReport:
    job_id: str
    checks: list[PreflightCheck]

    @property
    def ok(self) -> bool:
        return not any(check.status == PreflightStatus.FAIL for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
        }

    def summary(self) -> str:
        failed = [check for check in self.checks if check.status == PreflightStatus.FAIL]
        warnings = [check for check in self.checks if check.status == PreflightStatus.WARNING]
        if failed:
            return f"{len(failed)} preflight check(s) failed"
        if warnings:
            return f"Preflight passed with {len(warnings)} warning(s)"
        return "Preflight passed"


class PreflightRunner:
    def __init__(self, secret_store: SecretStore) -> None:
        self.secret_store = secret_store
        load_builtin_plugins()

    async def run(self, job: JobConfig) -> PreflightReport:
        checks: list[PreflightCheck] = []
        self._check_configuration(job, checks)
        self._check_plugin(job, checks)
        if self._has_failures(checks):
            return PreflightReport(job.id, checks)

        adapter = create_adapter(job)
        try:
            await adapter.connect()
            checks.append(self._pass("RPC connection", f"Connected to {job.chain} RPC"))
            signer_address = await self._check_wallet(job, adapter, checks)
            contract_ready = await self._check_contract(job, adapter, checks)
            await self._check_transaction_simulation(job, adapter, signer_address, contract_ready, checks)
        except Exception as exc:
            checks.append(self._fail("RPC connection", str(exc)))
        finally:
            await adapter.close()

        return PreflightReport(job.id, checks)

    def _check_configuration(self, job: JobConfig, checks: list[PreflightCheck]) -> None:
        result = validate_job(job)
        for error in result.errors:
            checks.append(self._fail("Configuration", error))
        for warning in result.warnings:
            checks.append(self._warning("Configuration", warning))
        if result.ok:
            checks.append(self._pass("Configuration", "Required job fields are present"))

    def _check_plugin(self, job: JobConfig, checks: list[PreflightCheck]) -> None:
        try:
            plugin_type = registry.get(job.job_type)
            plugin = plugin_type(job)
            plugin_errors = plugin.validate()
        except Exception as exc:
            checks.append(self._fail("Job plugin", str(exc)))
            return
        for error in plugin_errors:
            checks.append(self._fail("Job plugin", error))
        if not plugin_errors:
            checks.append(self._pass("Job plugin", f"{plugin_type.metadata().name} accepted the job"))

    async def _check_wallet(
        self,
        job: JobConfig,
        adapter: object,
        checks: list[PreflightCheck],
    ) -> str | None:
        if isinstance(adapter, MockChainAdapter):
            checks.append(self._pass("Wallet key", "Mock jobs do not require a private key"))
            return None
        if not job.wallet.private_key_ref:
            checks.append(self._fail("Wallet key", "Real EVM jobs require an imported private key"))
            return None
        try:
            signer_address = PrivateKeySigner(self.secret_store).address_for_ref(job.wallet.private_key_ref)
        except Exception as exc:
            checks.append(self._fail("Wallet key", str(exc)))
            return None
        configured = job.wallet.address.lower()
        if configured.startswith("0x") and len(configured) == 42 and configured != signer_address.lower():
            checks.append(
                self._fail(
                    "Wallet key",
                    f"Private key address {signer_address} does not match wallet {job.wallet.address}",
                )
            )
            return None
        checks.append(self._pass("Wallet key", f"Private key decrypts for {signer_address}"))
        return signer_address

    async def _check_contract(
        self,
        job: JobConfig,
        adapter: object,
        checks: list[PreflightCheck],
    ) -> bool:
        if not job.contract:
            checks.append(self._warning("Contract", "No contract configured; mock execution or plugin logic must supply payloads"))
            return False

        get_code = getattr(adapter, "get_code", None)
        if callable(get_code):
            code = await get_code(job.contract.address)
            if code in ("", "0x", b""):
                checks.append(self._fail("Contract", f"No bytecode found at {job.contract.address}"))
                return False
            else:
                checks.append(self._pass("Contract", f"Contract bytecode found at {job.contract.address}"))

        if not job.contract.abi_path:
            checks.append(self._warning("ABI", "No ABI path configured; real EVM execution needs an ABI"))
            return False
        abi = self._load_abi(job.contract.abi_path, checks)
        if abi is None:
            return False
        if self._abi_has_function(abi, job.execution.function_name):
            checks.append(self._pass("ABI", f"ABI exposes {job.execution.function_name}"))
            return True
        else:
            checks.append(self._fail("ABI", f"ABI does not expose {job.execution.function_name}"))
            return False

    async def _check_transaction_simulation(
        self,
        job: JobConfig,
        adapter: object,
        signer_address: str | None,
        contract_ready: bool,
        checks: list[PreflightCheck],
    ) -> None:
        if isinstance(adapter, MockChainAdapter):
            checks.append(self._pass("Simulation", "Mock transaction path can estimate gas"))
            return
        if signer_address is None or not contract_ready:
            checks.append(self._warning("Simulation", "Skipped until wallet, contract, and ABI checks pass"))
            return
        try:
            simulation = await TransactionSimulator(adapter).simulate(job, signer_address)  # type: ignore[arg-type]
        except Exception as exc:
            checks.append(self._fail("Simulation", str(exc)))
            return
        checks.append(self._pass("Simulation", simulation.summary()))

    def _load_abi(self, abi_path: str, checks: list[PreflightCheck]) -> list[dict[str, Any]] | None:
        path = Path(abi_path)
        if not path.exists():
            checks.append(self._fail("ABI", f"ABI file not found: {abi_path}"))
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            checks.append(self._fail("ABI", f"Could not read ABI: {exc}"))
            return None
        if isinstance(data, dict) and "abi" in data:
            data = data["abi"]
        if not isinstance(data, list):
            checks.append(self._fail("ABI", "ABI file must contain a list or an object with an 'abi' key"))
            return None
        return [item for item in data if isinstance(item, dict)]

    def _abi_has_function(self, abi: list[dict[str, Any]], function_name: str) -> bool:
        return any(item.get("type") == "function" and item.get("name") == function_name for item in abi)

    def _has_failures(self, checks: list[PreflightCheck]) -> bool:
        return any(check.status == PreflightStatus.FAIL for check in checks)

    def _pass(self, name: str, message: str) -> PreflightCheck:
        return PreflightCheck(name, PreflightStatus.PASS, message)

    def _warning(self, name: str, message: str) -> PreflightCheck:
        return PreflightCheck(name, PreflightStatus.WARNING, message)

    def _fail(self, name: str, message: str) -> PreflightCheck:
        return PreflightCheck(name, PreflightStatus.FAIL, message)
