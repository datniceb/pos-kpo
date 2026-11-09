import json
import os
from datetime import date

from pos.domain.errors import DomainError
from pos.domain.evaluation import Evaluation
from pos.domain.ports import RubricRepository, StudentRepository
from pos.domain.rubric import Rubric, RubricBuilder
from pos.domain.student import Student


class StorageError(Exception):
    """Файл с данными повреждён или не читается."""


# что может вылететь, если в файле руками что-то испортили: нет ключа, не тот тип, кривое число и т.п.
BROKEN_DATA_ERRORS = (KeyError, TypeError, ValueError, AttributeError, DomainError)


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:  # ValueError ловит и битый JSON, и файл не в UTF-8
        raise StorageError(f"Не удалось прочитать {path}: {e}") from e


def _write_json(path: str, data) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class JsonRubricRepository(RubricRepository):
    """Адаптер: рубрикатор в JSON-файле. Здесь же маппинг «словарь из файла ↔ доменный объект»."""

    def __init__(self, path: str):
        self._path = path

    def get(self) -> Rubric:
        data = _read_json(self._path, {"criteria": []})
        builder = RubricBuilder()
        try:
            for item in data["criteria"]:
                builder.add(item["name"], float(item["max_score"]), float(item["weight"]), item["id"])
            # если в файле кривые данные, Builder/Criterion бросят DomainError
            return builder.build(allow_empty=True)
        except BROKEN_DATA_ERRORS as e:
            raise StorageError(f"Файл {self._path} повреждён: {e}") from e

    def save(self, rubric: Rubric) -> None:
        criteria = []
        for c in rubric.criteria():
            criteria.append({"id": c.id, "name": c.name, "max_score": c.max_score, "weight": c.weight})
        _write_json(self._path, {"criteria": criteria})


class JsonStudentRepository(StudentRepository):
    """Адаптер: студенты и их оценки в JSON-файле.

    В файле у оценки хранится только id критерия, а при загрузке
    объект критерия берётся из рубрикатора.
    """

    def __init__(self, path: str, rubrics: RubricRepository):
        self._path = path
        self._rubrics = rubrics

    def save(self, student: Student) -> None:
        students = self.list_all()
        replaced = False
        for i in range(len(students)):
            if students[i].id == student.id:
                students[i] = student
                replaced = True
        if not replaced:
            students.append(student)
        _write_json(self._path, {"students": [self._to_dict(s) for s in students]})

    def get(self, student_id: str) -> Student | None:
        for student in self.list_all():
            if student.id == student_id:
                return student
        return None

    def list_all(self) -> list[Student]:
        data = _read_json(self._path, {"students": []})
        rubric = self._rubrics.get()
        try:
            return [self._from_dict(item, rubric) for item in data["students"]]
        except BROKEN_DATA_ERRORS as e:
            raise StorageError(f"Файл {self._path} повреждён: {e}") from e

    @staticmethod
    def _to_dict(student: Student) -> dict:
        evaluations = []
        for e in student.evaluations():
            evaluations.append(
                {
                    "criterion_id": e.criterion.id,
                    "score": e.score,
                    "comment": e.comment,
                    "date": e.created.isoformat(),
                }
            )
        return {"id": student.id, "name": student.name, "evaluations": evaluations}

    @staticmethod
    def _from_dict(item: dict, rubric: Rubric) -> Student:
        student = Student(item["name"], item["id"])
        for e in item["evaluations"]:
            if not rubric.has(e["criterion_id"]):
                # критерий удалили из рубрикатора руками — такую оценку просто не загружаем
                continue
            evaluation = Evaluation(
                rubric.get(e["criterion_id"]),
                float(e["score"]),
                e.get("comment", ""),
                date.fromisoformat(e["date"]),
            )
            student.put_evaluation(evaluation, rubric)
        return student
