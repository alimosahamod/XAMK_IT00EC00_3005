from application.commands.dto import CommandLogDto
from infrastructure.persistence.models import CommandLogRow


def command_log_to_dto(row: CommandLogRow) -> CommandLogDto:
    """Wandelt eine command_log-Zeile in das API-Lesemodell um."""
    return CommandLogDto(
        id=row.id,
        command_type=row.command_type,
        device_id=row.device_id,
        payload=dict(row.payload),
        status=row.status,
        error_message=row.error_message,
        created_at=row.created_at,
    )


def command_logs_to_dtos(rows: list[CommandLogRow]) -> list[CommandLogDto]:
    return [command_log_to_dto(row) for row in rows]
