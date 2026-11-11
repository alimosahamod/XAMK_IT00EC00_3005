from typing import Protocol
from uuid import UUID

from domain.commands.base import Command, CommandResult
from domain.commands.errors import CommandRejectedError


class CommandLog(Protocol):
    """Was der Invoker zum Protokollieren braucht (CommandLogRepository erfuellt das)."""

    def add(
        self, command_type: str, device_id: UUID, payload: dict, status: str, error_message: str | None
    ) -> None: ...


class CommandInvoker:
    """Invoker: fuehrt beliebige Commands aus und schreibt JEDEN Versuch ins command_log.

    Er kennt keine konkreten Befehle - nur `execute()` (Polymorphie).
    Aus dem Ausgang von execute() wird der Status:
      - kein Fehler             -> "success"
      - CommandRejectedError    -> "rejected" (Guard hat abgelehnt, nichts geaendert)
      - jeder andere Fehler     -> "failed"   (z.B. Decorator-Policy blockiert)
    """

    def __init__(self, log: CommandLog):
        self._log = log

    def submit(self, command: Command) -> CommandResult:
        try:
            command.execute()
            result = CommandResult("success")
        except CommandRejectedError as exc:
            result = CommandResult("rejected", str(exc))
        except Exception as exc:  # noqa: BLE001 - bewusst: jeder Port-Fehler soll als "failed" ins Log
            result = CommandResult("failed", str(exc))

        # Audit: auch rejected/failed bekommen eine Zeile.
        self._log.add(command.command_type, command.device_id, command.payload, result.status, result.error_message)
        return result
