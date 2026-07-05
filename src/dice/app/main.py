from __future__ import annotations

from textual.app import App, ComposeResult

from dice.core.manager import JobManager
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.service.client import RemoteJobManager, service_is_available
from dice.ui.dashboard import Dashboard


class DiceApp(App[None]):
    CSS = """
    Screen {
        background: $surface;
    }
    """
    TITLE = "DICE"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, manager: JobManager | None = None) -> None:
        super().__init__()
        if manager is not None:
            self.manager = manager
        elif service_is_available():
            self.manager = RemoteJobManager()
        else:
            self.manager = JobManager()

    def compose(self) -> ComposeResult:
        yield Dashboard(self.manager)

    def on_mount(self) -> None:
        jobs = self.manager.load_jobs()
        if not jobs and not getattr(self.manager, "is_remote", False):
            self.manager.create_job(
                JobConfig(
                    id=self.manager.store.next_id(),
                    name="Example Manual Sweep",
                    chain="ethereum",
                    wallet=WalletConfig(
                        name="Development Wallet",
                        address="0x0000000000000000000000000000000000000000",
                        destination="0x0000000000000000000000000000000000000000",
                    ),
                    rpc=RpcConfig(http_url="mock://local"),
                    trigger=TriggerConfig(kind=TriggerKind.MANUAL),
                    execution=ExecutionConfig(function_name="claim", arguments=[]),
                )
            )
        self.manager.add_listener(lambda _: self.call_later(self._refresh_dashboard))
        self._refresh_dashboard()

    async def on_unmount(self) -> None:
        if not getattr(self.manager, "is_remote", False):
            await self.manager.stop_all()

    def _refresh_dashboard(self) -> None:
        dashboard = self.query_one(Dashboard)
        dashboard.refresh_jobs()


def run() -> None:
    DiceApp().run()


if __name__ == "__main__":
    run()
