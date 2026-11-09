from abc import ABC, abstractmethod

from pos.domain.rubric import Rubric
from pos.domain.student import Student


class StudentRepository(ABC):
    """Порт хранения студентов. Реализация (JSON, память) — снаружи домена."""

    @abstractmethod
    def save(self, student: Student) -> None: ...

    @abstractmethod
    def get(self, student_id: str) -> Student | None: ...

    @abstractmethod
    def list_all(self) -> list[Student]: ...


class RubricRepository(ABC):
    """Порт хранения рубрикатора. Курс один, поэтому и рубрикатор один."""

    @abstractmethod
    def get(self) -> Rubric: ...

    @abstractmethod
    def save(self, rubric: Rubric) -> None: ...
