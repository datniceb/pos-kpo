import uuid

from pos.domain.errors import DomainError
from pos.domain.evaluation import Evaluation
from pos.domain.rubric import Rubric


class Student:
    """Студент — Entity и корень агрегата: внутри хранятся его оценки.

    По каждому критерию у студента не больше одной оценки.
    Повторное выставление оценки по тому же критерию = исправление.
    """

    def __init__(self, name: str, student_id: str | None = None):
        name = name.strip()
        if not name:
            raise DomainError("Имя студента не может быть пустым")
        self._id = student_id if student_id is not None else uuid.uuid4().hex[:8]
        self._name = name
        self._evaluations: dict[str, Evaluation] = {}

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def put_evaluation(self, evaluation: Evaluation, rubric: Rubric) -> None:
        # второй рубеж: даже оценку, созданную в обход фабрики, проверяем по рубрикатору
        criterion_id = evaluation.criterion.id
        if not rubric.has(criterion_id):
            raise DomainError("Нельзя оценить критерий, которого нет в рубрикаторе")
        self._evaluations[criterion_id] = evaluation

    def cancel_evaluation(self, criterion_id: str) -> None:
        if criterion_id not in self._evaluations:
            raise DomainError("У студента нет оценки по этому критерию")
        del self._evaluations[criterion_id]

    def remove_evaluations_for(self, criterion_id: str) -> None:
        """Вызывается при удалении критерия: оценок по несуществующему критерию быть не должно."""
        self._evaluations.pop(criterion_id, None)

    def evaluation_for(self, criterion_id: str) -> Evaluation | None:
        return self._evaluations.get(criterion_id)

    def evaluations(self) -> list[Evaluation]:
        return list(self._evaluations.values())

    def __eq__(self, other):
        return isinstance(other, Student) and self._id == other._id

    def __hash__(self):
        return hash(self._id)

    def __repr__(self):
        return f"Student({self._name!r})"
