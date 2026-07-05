from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dice.jobs.base import JobPlugin


@dataclass(frozen=True, slots=True)
class JobTypeMetadata:
    key: str
    name: str
    description: str
    trigger_kinds: list[str]
    action_kinds: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class JobRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, type[JobPlugin]] = {}

    def register(self, plugin: type[JobPlugin]) -> type[JobPlugin]:
        metadata = plugin.metadata()
        if metadata.key in self._plugins:
            raise ValueError(f"Job plugin already registered: {metadata.key}")
        self._plugins[metadata.key] = plugin
        return plugin

    def get(self, key: str) -> type[JobPlugin]:
        try:
            return self._plugins[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._plugins))
            raise KeyError(f"Unknown job type '{key}'. Available: {available}") from exc

    def list(self) -> list[JobTypeMetadata]:
        return [plugin.metadata() for plugin in self._plugins.values()]


registry = JobRegistry()


def register_job(plugin: type[JobPlugin]) -> type[JobPlugin]:
    return registry.register(plugin)


def load_builtin_plugins() -> None:
    import dice.jobs.balance_trigger  # noqa: F401
    import dice.jobs.contract_call  # noqa: F401
    import dice.jobs.custom_workflow  # noqa: F401
    import dice.jobs.event_trigger  # noqa: F401
    import dice.jobs.scheduled_transfer  # noqa: F401
    import dice.jobs.stake_sweep  # noqa: F401
    import dice.jobs.token_sweep  # noqa: F401
    import dice.jobs.wallet_watch  # noqa: F401
