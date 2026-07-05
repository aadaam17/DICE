from __future__ import annotations

from dataclasses import dataclass

from dice.adapters.profiles import PROFILES
from dice.core.models import JobConfig, SweepAssetKind, TriggerKind


@dataclass(frozen=True, slots=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


class JobValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_job(job: JobConfig) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not job.id.strip():
        errors.append("Job id is required")
    if not job.name.strip():
        errors.append("Job name is required")
    if job.chain not in PROFILES:
        errors.append(f"Unsupported chain: {job.chain}")
    if not job.rpc.http_url.strip():
        errors.append("HTTP RPC endpoint is required")
    if not job.wallet.name.strip():
        errors.append("Wallet name is required")
    if not _looks_like_address(job.wallet.address):
        warnings.append("Wallet address does not look like a normal EVM address")
    if not _looks_like_address(job.wallet.destination):
        warnings.append("Destination address does not look like a normal EVM address")
    if not job.execution.function_name.strip():
        errors.append("Execution function is required")

    if job.execution.asset_kind == SweepAssetKind.ERC20:
        if not job.execution.token_contract:
            errors.append("ERC20 sweep requires a token contract")
        if not job.execution.token_symbol:
            warnings.append("ERC20 sweep should include a token symbol")

    if job.trigger.kind == TriggerKind.EVENT:
        _require_trigger_param(job, "event_name", errors)
        _require_trigger_param(job, "event_signature", warnings)
    elif job.trigger.kind == TriggerKind.TIMESTAMP:
        _require_positive_int(job.trigger.params.get("timestamp"), "Unlock timestamp", errors)
    elif job.trigger.kind == TriggerKind.BLOCK:
        _require_positive_int(job.trigger.params.get("block"), "Unlock block", errors)
    elif job.trigger.kind == TriggerKind.CLAIMABLE_FUNCTION:
        _require_trigger_param(job, "function_name", errors)
    elif job.trigger.kind == TriggerKind.BALANCE_CHANGE:
        _require_trigger_param(job, "address", errors)

    if job.gas.replacement_percent < 0:
        errors.append("Replacement percent cannot be negative")
    if job.gas.priority_fee_gwei is not None and job.gas.priority_fee_gwei < 0:
        errors.append("Priority fee cannot be negative")
    if job.gas.max_fee_gwei is not None and job.gas.max_fee_gwei < 0:
        errors.append("Max fee cannot be negative")

    return ValidationResult(errors=errors, warnings=warnings)


def ensure_valid_job(job: JobConfig) -> ValidationResult:
    result = validate_job(job)
    if not result.ok:
        raise JobValidationError(result.errors)
    return result


def _looks_like_address(value: str) -> bool:
    return value.startswith("0x") and len(value) == 42


def _require_trigger_param(job: JobConfig, key: str, issues: list[str]) -> None:
    value = job.trigger.params.get(key)
    if value in (None, ""):
        issues.append(f"Trigger parameter '{key}' is required for {job.trigger.kind.value}")


def _require_positive_int(value: object, label: str, errors: list[str]) -> None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        errors.append(f"{label} must be an integer")
        return
    if parsed <= 0:
        errors.append(f"{label} must be greater than zero")
