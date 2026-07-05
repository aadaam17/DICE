from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from dice.core.workflow import WorkflowSpec


class JobStatus(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    SAVED = "saved"
    LOADED = "loaded"
    RUNNING = "running"
    WAITING = "waiting"
    TRIGGERED = "triggered"
    BROADCASTING = "broadcasting"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class TriggerKind(StrEnum):
    EVENT = "event"
    TIMESTAMP = "timestamp"
    BLOCK = "block"
    CLAIMABLE_FUNCTION = "claimable_function"
    BALANCE_CHANGE = "balance_change"
    MANUAL = "manual"


class SweepAssetKind(StrEnum):
    NATIVE = "native"
    ERC20 = "erc20"


class GasMode(StrEnum):
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    ULTRA = "ultra"
    CUSTOM = "custom"


@dataclass(slots=True)
class WalletConfig:
    name: str
    address: str
    destination: str
    private_key_ref: str | None = None


@dataclass(slots=True)
class RpcConfig:
    http_url: str
    websocket_url: str | None = None


@dataclass(slots=True)
class ContractConfig:
    address: str
    abi_path: str | None = None


@dataclass(slots=True)
class TriggerConfig:
    kind: TriggerKind
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionConfig:
    function_name: str
    arguments: list[Any] = field(default_factory=list)
    asset_kind: SweepAssetKind = SweepAssetKind.NATIVE
    token_contract: str | None = None
    token_symbol: str | None = None


@dataclass(slots=True)
class GasConfig:
    mode: GasMode = GasMode.STANDARD
    max_fee_gwei: float | None = None
    priority_fee_gwei: float | None = None
    replacement_percent: int = 15


@dataclass(slots=True)
class JobConfig:
    id: str
    name: str
    chain: str
    wallet: WalletConfig
    rpc: RpcConfig
    trigger: TriggerConfig
    execution: ExecutionConfig
    job_type: str = "contract_call"
    workflow: WorkflowSpec | None = None
    gas: GasConfig = field(default_factory=GasConfig)
    contract: ContractConfig | None = None
    enabled: bool = True
    status: JobStatus = JobStatus.CREATED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobConfig:
        return cls(
            id=data["id"],
            name=data["name"],
            chain=data["chain"],
            wallet=WalletConfig(**data["wallet"]),
            rpc=RpcConfig(**data["rpc"]),
            contract=ContractConfig(**data["contract"]) if data.get("contract") else None,
            trigger=TriggerConfig(
                kind=TriggerKind(data["trigger"]["kind"]),
                params=data["trigger"].get("params", {}),
            ),
            execution=ExecutionConfig(
                function_name=data["execution"]["function_name"],
                arguments=data["execution"].get("arguments", []),
                asset_kind=SweepAssetKind(data["execution"].get("asset_kind", SweepAssetKind.NATIVE)),
                token_contract=data["execution"].get("token_contract"),
                token_symbol=data["execution"].get("token_symbol"),
            ),
            job_type=data.get("job_type", "contract_call"),
            workflow=WorkflowSpec.from_dict(data["workflow"]) if data.get("workflow") else None,
            gas=GasConfig(
                mode=GasMode(data.get("gas", {}).get("mode", GasMode.STANDARD)),
                max_fee_gwei=data.get("gas", {}).get("max_fee_gwei"),
                priority_fee_gwei=data.get("gas", {}).get("priority_fee_gwei"),
                replacement_percent=data.get("gas", {}).get("replacement_percent", 15),
            ),
            enabled=data.get("enabled", True),
            status=JobStatus(data.get("status", JobStatus.CREATED)),
        )
