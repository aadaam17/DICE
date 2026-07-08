from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from dice.adapters.profiles import PROFILES
from dice.core.models import (
    ContractConfig,
    ExecutionConfig,
    GasConfig,
    GasMode,
    JobConfig,
    JobStatus,
    RpcConfig,
    SweepAssetKind,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.validation import JobValidationError, validate_job


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class Dashboard(Container):
    DEFAULT_CSS = """
    Dashboard {
        layout: vertical;
        height: 100%;
    }

    #hint {
        padding: 0 1;
        color: $text-muted;
    }

    #content {
        height: 1fr;
    }

    #sidebar {
        width: 18;
        padding: 1 1 0 1;
        border-right: solid $primary;
    }

    #sidebar_title {
        text-style: bold;
        padding-bottom: 1;
    }

    #sidebar Button {
        width: 14;
        margin-bottom: 1;
    }

    #main {
        width: 3fr;
        padding: 0 1;
    }

    #job_actions {
        height: 5;
        border-bottom: solid $primary;
    }

    #job_actions Button {
        width: 9;
        height: 3;
        margin-right: 1;
    }

    #delete {
        width: 10;
    }

    #duplicate {
        width: 11;
    }

    #jobs {
        height: 1fr;
    }

    #workflow {
        width: 1fr;
        padding: 0 1;
        border-left: solid $primary;
    }

    #workflow_title {
        text-style: bold;
        padding-bottom: 1;
    }

    #workflow_body {
        height: 10;
        color: $text-muted;
    }

    #field_1, #field_2, #field_3, #field_4 {
        margin-bottom: 1;
    }

    #details {
        height: 4;
        padding: 0 1;
        color: $text-muted;
        border-top: solid $primary;
    }
    """

    def __init__(self, manager: object) -> None:
        super().__init__()
        self.manager = manager
        self.view = "home"
        self.wizard_step = 0
        self.wizard_data: dict[str, Any] = {}
        self.editing_job_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        mode = "Daemon attached" if getattr(self.manager, "is_remote", False) else "Embedded mode"
        yield Static(f"DICE - {mode}", id="hint")
        with Horizontal(id="content"):
            with Vertical(id="sidebar"):
                yield Static("DICE", id="sidebar_title")
                yield Button("Home", id="home")
                yield Button("Create Job", id="create", variant="primary")
                yield Button("View Jobs", id="view_jobs")
                yield Button("Logs", id="logs")
                yield Button("Settings", id="settings")
                yield Button("Exit", id="exit")
            with Vertical(id="main"):
                with Horizontal(id="job_actions"):
                    yield Button("Start", id="start", variant="success")
                    yield Button("Check", id="preflight")
                    yield Button("Stop", id="stop", variant="warning")
                    yield Button("Edit", id="edit")
                    yield Button("Duplicate", id="duplicate")
                    yield Button("Delete", id="delete", variant="error")
                    yield Button("Refresh", id="refresh")
                table = DataTable(id="jobs")
                table.cursor_type = "row"
                table.add_columns("ID", "Name", "Chain", "Status", "Message", "Tx")
                yield table
            with Vertical(id="workflow"):
                yield Static("", id="workflow_title")
                yield Static("", id="workflow_body")
                yield Input(id="field_1")
                yield Input(id="field_2")
                yield Input(id="field_3")
                yield Input(id="field_4", password=True)
                with Horizontal(id="workflow_actions"):
                    yield Button("Back", id="back")
                    yield Button("Continue", id="continue")
                    yield Button("Save Job", id="save")
                    yield Button("Cancel", id="cancel")
        yield Static("", id="details")
        yield Footer()

    def on_mount(self) -> None:
        self.manager.load_jobs()
        self.refresh_jobs()
        self._show_home()

    def refresh_jobs(self) -> None:
        if getattr(self.manager, "is_remote", False):
            self.manager.load_jobs()

        table = self.query_one("#jobs", DataTable)
        table.clear()
        for job in sorted(self.manager.jobs.values(), key=lambda item: item.id):
            state = self.manager.states.get(job.id)
            status = state.status if state else JobStatus.LOADED
            message = state.message if state else ""
            tx_hash = state.tx_hash[:12] + "..." if state and state.tx_hash else ""
            table.add_row(job.id, job.name, job.chain, status.value, message, tx_hash, key=job.id)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "home":
            self._show_home()
            return
        if button_id == "create":
            self._start_create()
            return
        if button_id == "view_jobs":
            self.refresh_jobs()
            self._show_jobs_help()
            return
        if button_id == "settings":
            self._show_settings()
            return
        if button_id == "exit":
            self.app.exit()
            return
        if button_id == "back":
            self._wizard_back()
            return
        if button_id == "continue":
            self._wizard_continue()
            return
        if button_id == "save":
            self._save_wizard_job()
            return
        if button_id == "cancel":
            self._show_home()
            return

        job_id = self._selected_job_id()
        if not job_id:
            self._set_details("No job selected.")
            return

        if button_id == "start":
            try:
                self._set_details(f"Starting {job_id}; running preflight first.")
                await self.manager.start(job_id)
                self.refresh_jobs()
            except Exception as exc:
                self._set_details(f"Cannot start {job_id}: {exc}")
            return
        if button_id == "preflight":
            try:
                await self._run_preflight(job_id)
            except Exception as exc:
                self._set_details(f"Cannot check {job_id}: {exc}")
            return
        if button_id == "stop":
            try:
                await self.manager.stop(job_id)
                self.refresh_jobs()
            except Exception as exc:
                self._set_details(f"Cannot stop {job_id}: {exc}")
            return
        if button_id == "delete":
            try:
                await self.manager.delete(job_id)
                self.refresh_jobs()
                self._set_details(f"Deleted {job_id}.")
            except Exception as exc:
                self._set_details(f"Cannot delete {job_id}: {exc}")
            return
        if button_id == "logs":
            self._show_logs(job_id)
            return
        if button_id == "duplicate":
            self._duplicate_job(job_id)
            return
        if button_id == "edit":
            self._start_edit(job_id)
            return

    def _show_home(self) -> None:
        self.view = "home"
        self._clear_inputs()
        self._set_wizard_controls(False)
        self._set_workflow(
            "Welcome to DICE",
            "\n".join(
                [
                    "Create Job",
                    "View Jobs",
                    "Global Settings",
                    "Exit",
                    "",
                    "Open the daemon in the background, then use this TUI as the operator console.",
                ]
            ),
        )
        self._set_details("Jobs are owned by the daemon. Closing the TUI does not stop daemon jobs.")

    def _show_jobs_help(self) -> None:
        self.view = "jobs"
        self._clear_inputs()
        self._set_wizard_controls(False)
        self._set_workflow(
            "Active Jobs",
            "Select a job row, then choose Check, Start, Stop, Edit, Duplicate, Delete, or Logs.",
        )
        self._set_details("Every job runs independently with its own watcher, trigger, and executor.")

    def _show_settings(self) -> None:
        chains = ", ".join(profile.name for profile in PROFILES.values())
        job_types = self._job_type_summary()
        wallets = self._wallet_summary()
        self._clear_inputs()
        self._set_wizard_controls(False)
        self._set_workflow(
            "Global Settings",
            "\n".join(
                [
                    "Daemon: 127.0.0.1:8765",
                    "Job storage: storage/jobs",
                    "Runtime logs: daemon memory in this build",
                    "",
                    f"Supported chains: {chains}",
                    "",
                    f"Job plugins: {job_types}",
                    "",
                    f"Wallet vault: {wallets}",
                ]
            ),
        )
        self._set_details("Chain support comes from chain profiles, not hardcoded UI branches.")

    def _start_create(self) -> None:
        self.view = "create"
        self.editing_job_id = None
        self.wizard_step = 0
        self.wizard_data = {}
        self._render_wizard()

    def _start_edit(self, job_id: str) -> None:
        job = self.manager.jobs[job_id]
        self.view = "edit"
        self.editing_job_id = job_id
        self.wizard_step = 0
        self.wizard_data = self._job_to_wizard_data(job)
        self._render_wizard()

    def _wizard_continue(self) -> None:
        if self.view not in {"create", "edit"}:
            return
        self._capture_wizard_step()
        self.wizard_step = min(self.wizard_step + 1, 9)
        self._render_wizard()

    def _wizard_back(self) -> None:
        if self.view not in {"create", "edit"}:
            return
        self._capture_wizard_step()
        self.wizard_step = max(self.wizard_step - 1, 0)
        self._render_wizard()

    def _render_wizard(self) -> None:
        title, body, placeholders = self._wizard_step_content()
        self._set_workflow(title, body)
        values = self._wizard_step_values()
        for index, input_id in enumerate(self._field_ids()):
            field = self.query_one(input_id, Input)
            placeholder = placeholders[index] if index < len(placeholders) else ""
            field.placeholder = placeholder
            field.value = values[index] if index < len(values) else ""
            field.display = bool(placeholder)
            field.password = self.wizard_step == 3 and input_id == "#field_2"
        self._set_wizard_controls(True)
        self._set_details("Continue through each screen, then review the summary and choose Save Job.")

    def _wizard_step_content(self) -> tuple[str, str, list[str]]:
        chain_list = "\n".join(f"- {profile.name} ({key})" for key, profile in PROFILES.items())
        job_type_list = self._job_type_option_text()
        job_type = self._selected_job_type()
        steps = [
            (
                "Select Job Type",
                f"Choose a workflow plugin by key.\n\n{job_type_list}",
                ["Job type key, e.g. contract_call", "", ""],
            ),
            (
                "Select Blockchain",
                f"Choose a supported EVM chain by key.\n\n{chain_list}",
                ["Chain key, e.g. ethereum", "", ""],
            ),
            (
                "RPC Endpoint",
                "Use mock://local for dry-run testing. Use HTTP/WebSocket RPC endpoints for real EVM execution.",
                ["HTTP RPC", "WebSocket RPC optional", ""],
            ),
            (
                "Wallet Configuration",
                "Enter the private key once. DICE encrypts it and stores only a secret reference.",
                ["Wallet name", "Private key", "Wallet address", "Destination wallet"],
            ),
            (
                "Sweep Type",
                "Choose what happens after unlock: native coin or ERC20 token.",
                ["native or erc20", "Token contract if ERC20", "Token symbol if ERC20"],
            ),
            (
                "Staking Information",
                "Provide the staking contract and optional ABI path.",
                ["Staking contract", "ABI path optional", ""],
            ),
            (
                "Unlock Method",
                "manual, event, timestamp, block, claimable_function, or balance_change.",
                ["Unlock method, e.g. manual", "Parameter 1", "Parameter 2"],
            ),
            (
                "Withdrawal Function",
                "Define the execution function and comma-separated arguments.",
                ["Function name, e.g. withdraw", "Arguments, e.g. poolId", ""],
            ),
            (
                "Gas Strategy",
                "standard, aggressive, ultra, or custom. Custom can include priority and max fee.",
                ["Gas mode", "Priority fee gwei", "Max fee gwei"],
            ),
            (
                "Retry Policy And Summary",
                self._summary_text(),
                ["Replacement percent", "", ""],
            ),
        ]
        title, body, placeholders = steps[self.wizard_step]
        step_name = {
            3: "wallet",
            4: "asset",
            5: "contract",
            6: "trigger",
            7: "execution",
        }.get(self.wizard_step)
        if step_name:
            hints = self._schema_fields_for_step(job_type, step_name)
            if hints:
                body = body + "\n\nFor this job type:\n" + "\n".join(
                    f"- {item['label']}: {item['placeholder']}" for item in hints
                )
                placeholders = self._dynamic_placeholders(step_name, placeholders, hints)
        return title, body, placeholders

    def _wizard_step_values(self) -> list[str]:
        values = {
            0: [self.wizard_data.get("job_type", "contract_call"), "", ""],
            1: [self.wizard_data.get("chain", "ethereum"), "", ""],
            2: [
                self.wizard_data.get("http_rpc", "http://localhost:8545"),
                self.wizard_data.get("websocket_rpc", ""),
                "",
            ],
            3: [
                self.wizard_data.get("wallet_name", ""),
                self.wizard_data.get("private_key", ""),
                self.wizard_data.get("wallet_address", ""),
                self.wizard_data.get("destination", ""),
            ],
            4: [
                self.wizard_data.get("asset_kind", self._job_type_default("asset_kind", "native")),
                self.wizard_data.get("token_contract", ""),
                self.wizard_data.get("token_symbol", ""),
            ],
            5: [self.wizard_data.get("contract_address", ""), self.wizard_data.get("abi_path", ""), ""],
            6: [
                self.wizard_data.get("trigger_kind", self._job_type_default("trigger_kind", "manual")),
                self.wizard_data.get("trigger_param_1", ""),
                self.wizard_data.get("trigger_param_2", ""),
            ],
            7: [
                self.wizard_data.get("function_name", self._job_type_default("function_name", "withdraw")),
                self.wizard_data.get("function_arguments", ""),
                "",
            ],
            8: [
                self.wizard_data.get("gas_mode", "standard"),
                self.wizard_data.get("priority_fee_gwei", ""),
                self.wizard_data.get("max_fee_gwei", ""),
            ],
            9: [self.wizard_data.get("replacement_percent", "15"), "", ""],
        }
        return values[self.wizard_step]

    def _capture_wizard_step(self) -> None:
        values = [self.query_one(input_id, Input).value.strip() for input_id in self._field_ids()]
        if self.wizard_step == 0:
            self.wizard_data["job_type"] = values[0] or "contract_call"
        elif self.wizard_step == 1:
            self.wizard_data["chain"] = values[0] or "ethereum"
        elif self.wizard_step == 2:
            self.wizard_data["http_rpc"] = values[0] or "http://localhost:8545"
            self.wizard_data["websocket_rpc"] = values[1]
        elif self.wizard_step == 3:
            self.wizard_data["wallet_name"] = values[0] or "Wallet"
            self.wizard_data["private_key"] = values[1]
            self.wizard_data["wallet_address"] = values[2] or ZERO_ADDRESS
            self.wizard_data["destination"] = values[3] or ZERO_ADDRESS
        elif self.wizard_step == 4:
            self.wizard_data["asset_kind"] = values[0] or self._job_type_default("asset_kind", "native")
            self.wizard_data["token_contract"] = values[1]
            self.wizard_data["token_symbol"] = values[2]
        elif self.wizard_step == 5:
            self.wizard_data["contract_address"] = values[0]
            self.wizard_data["abi_path"] = values[1]
        elif self.wizard_step == 6:
            self.wizard_data["trigger_kind"] = values[0] or self._job_type_default("trigger_kind", "manual")
            self.wizard_data["trigger_param_1"] = values[1]
            self.wizard_data["trigger_param_2"] = values[2]
        elif self.wizard_step == 7:
            self.wizard_data["function_name"] = values[0] or self._job_type_default("function_name", "withdraw")
            self.wizard_data["function_arguments"] = values[1]
        elif self.wizard_step == 8:
            self.wizard_data["gas_mode"] = values[0] or "standard"
            self.wizard_data["priority_fee_gwei"] = values[1]
            self.wizard_data["max_fee_gwei"] = values[2]
        elif self.wizard_step == 9:
            self.wizard_data["replacement_percent"] = values[0] or "15"

    def _save_wizard_job(self) -> None:
        if self.view not in {"create", "edit"}:
            return
        self._capture_wizard_step()
        try:
            job = self._build_job_from_wizard()
            validation = validate_job(job)
            if not validation.ok:
                self._set_details("Cannot save job: " + "; ".join(validation.errors))
                return
            private_key = self.wizard_data.get("private_key", "").strip()
            if private_key:
                job.wallet.private_key_ref = self._store_or_reuse_wallet_ref(job, private_key)
            self.manager.create_job(job)
        except JobValidationError as exc:
            self._set_details("Cannot save job: " + "; ".join(exc.errors))
            return
        except RuntimeError as exc:
            self._set_details(f"Cannot save job: {exc}")
            return
        self.refresh_jobs()
        self._show_jobs_help()
        action = "Updated" if self.editing_job_id else "Saved"
        self._set_details(f"{action} {job.id}: {job.name}")

    def _store_or_reuse_wallet_ref(self, job: JobConfig, value: str) -> str:
        if value.startswith("secret://wallets/"):
            return value
        wallet_id = self._wallet_id(job.wallet.name)
        import_wallet = getattr(self.manager, "import_wallet", None)
        if callable(import_wallet):
            return import_wallet(wallet_id, job.wallet.name, job.wallet.address, value)
        return self.manager.import_private_key(job.id, job.wallet.name, value)

    def _build_job_from_wizard(self) -> JobConfig:
        chain = self.wizard_data.get("chain", "ethereum")
        if chain not in PROFILES:
            chain = "ethereum"
        asset_kind = self._asset_kind(self.wizard_data.get("asset_kind", self._job_type_default("asset_kind", "native")))
        trigger_kind = self._trigger_kind(self.wizard_data.get("trigger_kind", self._job_type_default("trigger_kind", "manual")))
        gas_mode = self._gas_mode(self.wizard_data.get("gas_mode", "standard"))
        wallet_name = self.wizard_data.get("wallet_name", "Wallet")
        job_id = self.editing_job_id or self.manager.next_id()
        return JobConfig(
            id=job_id,
            name=f"{PROFILES[chain].name} - {wallet_name}",
            chain=chain,
            wallet=WalletConfig(
                name=wallet_name,
                address=self.wizard_data.get("wallet_address", ZERO_ADDRESS),
                destination=self.wizard_data.get("destination", ZERO_ADDRESS),
                private_key_ref=self.wizard_data.get("private_key_ref"),
            ),
            rpc=RpcConfig(
                http_url=self.wizard_data.get("http_rpc", "http://localhost:8545"),
                websocket_url=self.wizard_data.get("websocket_rpc") or None,
            ),
            contract=ContractConfig(
                address=self.wizard_data.get("contract_address", ""),
                abi_path=self.wizard_data.get("abi_path") or None,
            )
            if self.wizard_data.get("contract_address")
            else None,
            trigger=TriggerConfig(kind=trigger_kind, params=self._trigger_params(trigger_kind)),
            execution=ExecutionConfig(
                function_name=self.wizard_data.get("function_name", self._job_type_default("function_name", "withdraw")),
                arguments=self._split_arguments(self.wizard_data.get("function_arguments", "")),
                asset_kind=asset_kind,
                token_contract=self.wizard_data.get("token_contract") or None,
                token_symbol=self.wizard_data.get("token_symbol") or None,
            ),
            job_type=self.wizard_data.get("job_type", "contract_call"),
            gas=GasConfig(
                mode=gas_mode,
                priority_fee_gwei=self._float_or_none(self.wizard_data.get("priority_fee_gwei", "")),
                max_fee_gwei=self._float_or_none(self.wizard_data.get("max_fee_gwei", "")),
                replacement_percent=self._int_or_default(
                    self.wizard_data.get("replacement_percent", "15"), 15
                ),
            ),
        )

    def _job_to_wizard_data(self, job: JobConfig) -> dict[str, Any]:
        return {
            "job_type": job.job_type,
            "chain": job.chain,
            "http_rpc": job.rpc.http_url,
            "websocket_rpc": job.rpc.websocket_url or "",
            "wallet_name": job.wallet.name,
            "private_key": "",
            "private_key_ref": job.wallet.private_key_ref,
            "wallet_address": job.wallet.address,
            "destination": job.wallet.destination,
            "asset_kind": job.execution.asset_kind.value,
            "token_contract": job.execution.token_contract or "",
            "token_symbol": job.execution.token_symbol or "",
            "contract_address": job.contract.address if job.contract else "",
            "abi_path": job.contract.abi_path if job.contract and job.contract.abi_path else "",
            "trigger_kind": job.trigger.kind.value,
            "trigger_param_1": self._first_trigger_param(job.trigger.params),
            "trigger_param_2": self._second_trigger_param(job.trigger.params),
            "function_name": job.execution.function_name,
            "function_arguments": ", ".join(str(item) for item in job.execution.arguments),
            "gas_mode": job.gas.mode.value,
            "priority_fee_gwei": "" if job.gas.priority_fee_gwei is None else str(job.gas.priority_fee_gwei),
            "max_fee_gwei": "" if job.gas.max_fee_gwei is None else str(job.gas.max_fee_gwei),
            "replacement_percent": str(job.gas.replacement_percent),
        }

    def _duplicate_job(self, job_id: str) -> None:
        original = self.manager.jobs[job_id]
        data = original.to_dict()
        data["id"] = self.manager.next_id()
        data["name"] = f"{original.name} Copy"
        duplicate = JobConfig.from_dict(data)
        self.manager.create_job(duplicate)
        self.refresh_jobs()
        self._set_details(f"Duplicated {job_id} as {duplicate.id}.")

    def _show_logs(self, job_id: str) -> None:
        self._clear_inputs()
        self._set_wizard_controls(False)
        logs = self.manager.get_logs(job_id)
        if not logs:
            self._set_workflow("Logs", f"{job_id}: no runtime logs yet.")
            return
        self._set_workflow("Logs", "\n".join(logs[-8:]))

    async def _run_preflight(self, job_id: str) -> None:
        preflight = getattr(self.manager, "preflight", None)
        if preflight is None:
            self._set_details("Preflight is not available in this runtime.")
            return
        report = await preflight(job_id)
        self._show_preflight_report(report)

    def _show_preflight_report(self, report: object) -> None:
        self._clear_inputs()
        self._set_wizard_controls(False)
        if isinstance(report, dict):
            checks = list(report.get("checks", []))
            ok = bool(report.get("ok"))
        else:
            checks = [check.to_dict() for check in getattr(report, "checks", [])]
            ok = bool(getattr(report, "ok", False))
        rows = []
        for check in checks:
            status = str(check.get("status", "")).upper()
            name = str(check.get("name", "Check"))
            message = str(check.get("message", ""))
            rows.append(f"{status}: {name} - {message}")
        self._set_workflow("Preflight", "\n".join(rows[-10:]) if rows else "No checks returned.")
        self._set_details("Preflight passed. Job is ready to start." if ok else "Preflight failed. Fix the listed issue before starting.")

    def _selected_job_id(self) -> str | None:
        table = self.query_one("#jobs", DataTable)
        if table.cursor_row is None or not table.rows:
            return None
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        return str(row_key.value)

    def _set_workflow(self, title: str, body: str) -> None:
        self.query_one("#workflow_title", Static).update(title)
        self.query_one("#workflow_body", Static).update(body)

    def _set_details(self, message: str) -> None:
        self.query_one("#details", Static).update(message)

    def _clear_inputs(self) -> None:
        for input_id in self._field_ids():
            field = self.query_one(input_id, Input)
            field.value = ""
            field.placeholder = ""
            field.display = False
            field.password = False

    def _set_wizard_controls(self, visible: bool) -> None:
        for button_id in ["#back", "#continue", "#save", "#cancel"]:
            self.query_one(button_id, Button).display = visible

    def _field_ids(self) -> list[str]:
        return ["#field_1", "#field_2", "#field_3", "#field_4"]

    def _summary_text(self) -> str:
        return "\n".join(
            [
                f"Job type: {self.wizard_data.get('job_type', 'contract_call')}",
                f"Chain: {self.wizard_data.get('chain', 'ethereum')}",
                f"Wallet: {self.wizard_data.get('wallet_name', 'Wallet')}",
                f"Destination: {self.wizard_data.get('destination', ZERO_ADDRESS)}",
                f"Unlock: {self.wizard_data.get('trigger_kind', self._job_type_default('trigger_kind', 'manual'))}",
                f"Action: {self.wizard_data.get('function_name', self._job_type_default('function_name', 'withdraw'))}()",
                f"Gas: {self.wizard_data.get('gas_mode', 'standard')}",
            ]
        )

    def _trigger_params(self, kind: TriggerKind) -> dict[str, Any]:
        first = self.wizard_data.get("trigger_param_1", "")
        second = self.wizard_data.get("trigger_param_2", "")
        if kind == TriggerKind.EVENT:
            return {"event_name": first, "event_signature": second}
        if kind == TriggerKind.TIMESTAMP:
            return {"timestamp": self._int_or_default(first, 0)}
        if kind == TriggerKind.BLOCK:
            return {"block": self._int_or_default(first, 0)}
        if kind == TriggerKind.CLAIMABLE_FUNCTION:
            return {"function_name": first, "arguments": self._split_arguments(second)}
        if kind == TriggerKind.BALANCE_CHANGE:
            return {"address": first}
        return {}

    def _asset_kind(self, value: str) -> SweepAssetKind:
        try:
            return SweepAssetKind(value.lower())
        except ValueError:
            return SweepAssetKind.NATIVE

    def _trigger_kind(self, value: str) -> TriggerKind:
        normalized = value.lower().replace(" ", "_")
        if normalized == "block_number":
            normalized = "block"
        try:
            return TriggerKind(normalized)
        except ValueError:
            return TriggerKind.MANUAL

    def _gas_mode(self, value: str) -> GasMode:
        try:
            return GasMode(value.lower())
        except ValueError:
            return GasMode.STANDARD

    def _split_arguments(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _float_or_none(self, value: str) -> float | None:
        try:
            return float(value) if value else None
        except ValueError:
            return None

    def _int_or_default(self, value: str, default: int) -> int:
        try:
            return int(value) if value else default
        except ValueError:
            return default

    def _wallet_id(self, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "-")
        safe = "".join(character for character in normalized if character.isalnum() or character in "-_")
        return safe or "wallet"

    def _first_trigger_param(self, params: dict[str, Any]) -> str:
        for key in ["event_name", "timestamp", "block", "function_name", "address"]:
            if key in params:
                return str(params[key])
        return ""

    def _second_trigger_param(self, params: dict[str, Any]) -> str:
        if "event_signature" in params:
            return str(params["event_signature"])
        if "arguments" in params:
            return ", ".join(str(item) for item in params["arguments"])
        return ""

    def _selected_job_type(self) -> str:
        return str(self.wizard_data.get("job_type", "contract_call") or "contract_call")

    def _job_type_default(self, key: str, fallback: str) -> str:
        defaults = {
            "contract_call": {
                "trigger_kind": "manual",
                "function_name": "claim",
                "asset_kind": "native",
            },
            "stake_sweep": {
                "trigger_kind": "claimable_function",
                "function_name": "withdraw",
                "asset_kind": "native",
            },
            "token_sweep": {
                "trigger_kind": "balance_change",
                "function_name": "transfer",
                "asset_kind": "erc20",
            },
            "scheduled_transfer": {
                "trigger_kind": "timestamp",
                "function_name": "transfer",
                "asset_kind": "native",
            },
            "wallet_watch": {
                "trigger_kind": "balance_change",
                "function_name": "notify",
                "asset_kind": "native",
            },
            "balance_trigger": {
                "trigger_kind": "balance_change",
                "function_name": "notify",
                "asset_kind": "native",
            },
            "event_trigger": {
                "trigger_kind": "event",
                "function_name": "claim",
                "asset_kind": "native",
            },
            "custom_workflow": {
                "trigger_kind": "manual",
                "function_name": "notify",
                "asset_kind": "native",
            },
        }
        return defaults.get(self._selected_job_type(), {}).get(key, fallback)

    def _schema_fields_for_step(self, job_type: str, step: str) -> list[dict[str, str]]:
        for item in self._job_type_items():
            if self._metadata_value(item, "key") != job_type:
                continue
            fields = self._metadata_value(item, "form_fields") or []
            result: list[dict[str, str]] = []
            if not isinstance(fields, list):
                return result
            for field in fields:
                if not isinstance(field, dict) or field.get("step") != step:
                    continue
                result.append(
                    {
                        "key": str(field.get("key", "")),
                        "label": str(field.get("label", field.get("key", ""))),
                        "placeholder": str(field.get("placeholder", "")),
                    }
                )
            return result
        return []

    def _dynamic_placeholders(
        self,
        step: str,
        placeholders: list[str],
        hints: list[dict[str, str]],
    ) -> list[str]:
        by_key = {item["key"]: item["placeholder"] for item in hints}
        keys_by_step = {
            "wallet": ["wallet_name", "private_key", "wallet_address", "destination"],
            "asset": ["asset_kind", "token_contract", "token_symbol"],
            "contract": ["contract_address", "abi_path", ""],
            "trigger": ["trigger_kind", "trigger_param_1", "trigger_param_2"],
            "execution": ["function_name", "arguments", ""],
        }
        keys = keys_by_step.get(step, [])
        updated = list(placeholders)
        for index, key in enumerate(keys):
            if index < len(updated) and key in by_key:
                updated[index] = by_key[key]
        return updated

    def _job_type_items(self) -> list[object]:
        provider = getattr(self.manager, "available_job_types", None)
        if provider is None:
            return []
        return list(provider())

    def _metadata_value(self, item: object, key: str) -> object:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    def _job_type_summary(self) -> str:
        names: list[str] = []
        for item in self._job_type_items():
            if hasattr(item, "name"):
                names.append(str(item.name))
            elif isinstance(item, dict):
                names.append(str(item.get("name", item.get("key", "unknown"))))
        return ", ".join(names) if names else "none"

    def _wallet_summary(self) -> str:
        provider = getattr(self.manager, "list_wallets", None)
        if provider is None:
            return "unavailable"
        try:
            wallets = provider()
        except Exception:
            return "unavailable"
        labels: list[str] = []
        for wallet in wallets:
            if isinstance(wallet, dict):
                labels.append(str(wallet.get("ref", wallet.get("label", "wallet"))))
            elif hasattr(wallet, "ref"):
                labels.append(str(wallet.ref))
        return ", ".join(labels) if labels else "empty"

    def _job_type_option_text(self) -> str:
        rows: list[str] = []
        for item in self._job_type_items():
            if hasattr(item, "key") and hasattr(item, "name"):
                rows.append(f"- {item.key} ({item.name})")
            elif isinstance(item, dict):
                rows.append(f"- {item.get('key')} ({item.get('name')})")
        return "\n".join(rows) if rows else "- contract_call (Contract Call)"
