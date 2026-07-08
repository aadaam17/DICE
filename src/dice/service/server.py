from __future__ import annotations

import asyncio
import json
from typing import Any

from dice.core.manager import JobManager
from dice.core.models import JobConfig
from dice import __version__
from dice.service.client import DEFAULT_HOST, DEFAULT_PORT

PROTOCOL_VERSION = 1


class DiceService:
    def __init__(
        self,
        manager: JobManager | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.manager = manager or JobManager()
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self.manager.load_jobs()
        await self.manager.start_enabled()
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)

    async def serve_forever(self) -> None:
        await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        await self.manager.stop_all()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            raw = await reader.readline()
            request = json.loads(raw.decode("utf-8"))
            response = await self._dispatch(request)
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}

        writer.write(json.dumps(response).encode("utf-8") + b"\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        command = request.get("command")
        if command == "ping":
            return {"ok": True, "version": __version__, "protocol": PROTOCOL_VERSION}
        if command == "status":
            return {
                "ok": True,
                "version": __version__,
                "protocol": PROTOCOL_VERSION,
                "jobs": len(self.manager.jobs),
                "running": len(self.manager.snapshot()["running"]),  # type: ignore[arg-type]
            }
        if command == "list_jobs":
            return {"ok": True, **self.manager.snapshot()}
        if command == "list_job_types":
            return {"ok": True, "job_types": [item.to_dict() for item in self.manager.available_job_types()]}
        if command == "create_job":
            job = JobConfig.from_dict(request["job"])
            self.manager.create_job(job)
            return {"ok": True, **self.manager.snapshot()}
        if command == "import_private_key":
            private_key_ref = self.manager.import_private_key(
                request["job_id"],
                request.get("label", "Wallet"),
                request["private_key"],
            )
            return {"ok": True, "private_key_ref": private_key_ref}
        if command == "import_wallet":
            private_key_ref = self.manager.import_wallet(
                request["wallet_id"],
                request.get("label", request["wallet_id"]),
                request.get("address"),
                request["private_key"],
            )
            return {"ok": True, "private_key_ref": private_key_ref}
        if command == "list_wallets":
            return {"ok": True, "wallets": [wallet.to_dict() for wallet in self.manager.list_wallets()]}
        if command == "next_job_id":
            return {"ok": True, "job_id": self.manager.next_id()}
        if command == "preflight_job":
            report = await self.manager.preflight(request["job_id"])
            return {"ok": True, "report": report.to_dict()}
        if command == "start_job":
            await self.manager.start(request["job_id"])
            return {"ok": True, **self.manager.snapshot()}
        if command == "stop_job":
            await self.manager.stop(request["job_id"])
            return {"ok": True, **self.manager.snapshot()}
        if command == "delete_job":
            await self.manager.delete(request["job_id"])
            return {"ok": True, **self.manager.snapshot()}
        if command == "get_logs":
            return {"ok": True, "logs": self.manager.get_logs(request["job_id"])}
        raise ValueError(f"Unknown command: {command}")
