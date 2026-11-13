from abc import ABC, abstractmethod


class ResultExporter(ABC):
    """Исходящий порт экспорта итогов. Сценарий не знает, в какой формат идёт выгрузка."""

    @abstractmethod
    def export(self, rows: list[tuple[str, str, float]], path: str) -> None:
        """rows: (id студента, имя, итог)."""
