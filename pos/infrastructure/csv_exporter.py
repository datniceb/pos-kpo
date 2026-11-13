import csv
import os

from pos.application.ports import ResultExporter


class CsvResultExporter(ResultExporter):
    """Адаптер экспорта итогов в CSV.

    Разделитель «;» и кодировка utf-8-sig — чтобы русский Excel открывал файл без кракозябр.
    """

    def export(self, rows: list[tuple[str, str, float]], path: str) -> None:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Студент", "Итог"])
            for student_id, name, grade in rows:
                writer.writerow([student_id, name, f"{grade:g}"])
