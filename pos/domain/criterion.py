import math
import uuid

from pos.domain.errors import DomainError


class Criterion:
    """Критерий оценивания. Entity: у критерия есть id, по нему на него ссылаются оценки."""

    def __init__(self, name: str, max_score: float, weight: float, criterion_id: str | None = None):
        name = name.strip()
        if not name:
            raise DomainError("Название критерия не может быть пустым")
        # math.isfinite отсекает nan и inf, которые float() спокойно парсит из строки
        if not math.isfinite(max_score) or max_score <= 0:
            raise DomainError("Максимальный балл критерия должен быть конечным числом больше 0")
        if not math.isfinite(weight) or weight <= 0:
            raise DomainError("Вес критерия должен быть конечным числом больше 0")

        self._id = criterion_id if criterion_id is not None else uuid.uuid4().hex[:8]
        self._name = name
        self._max_score = float(max_score)
        self._weight = float(weight)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_score(self) -> float:
        return self._max_score

    @property
    def weight(self) -> float:
        return self._weight

    def __eq__(self, other):
        return isinstance(other, Criterion) and self._id == other._id

    def __hash__(self):
        return hash(self._id)

    def __repr__(self):
        return f"Criterion({self._name!r}, max={self._max_score}, weight={self._weight})"
