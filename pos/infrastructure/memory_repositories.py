from pos.domain.ports import RubricRepository, StudentRepository
from pos.domain.rubric import Rubric
from pos.domain.student import Student


class InMemoryStudentRepository(StudentRepository):
    """Адаптер для тестов и демо: всё хранится в словаре, без файлов."""

    def __init__(self):
        self._data: dict[str, Student] = {}

    def save(self, student: Student) -> None:
        self._data[student.id] = student

    def get(self, student_id: str) -> Student | None:
        return self._data.get(student_id)

    def list_all(self) -> list[Student]:
        return list(self._data.values())


class InMemoryRubricRepository(RubricRepository):
    def __init__(self):
        self._rubric = Rubric()

    def get(self) -> Rubric:
        return self._rubric

    def save(self, rubric: Rubric) -> None:
        self._rubric = rubric
