from pos.domain.criterion import Criterion
from pos.domain.errors import DomainError


class Rubric:
    """Рубрикатор — набор критериев курса. Корень агрегата."""

    def __init__(self):
        self._criteria: dict[str, Criterion] = {}

    def add_criterion(self, criterion: Criterion) -> None:
        if criterion.id in self._criteria:
            raise DomainError("Критерий с таким id уже есть в рубрикаторе")
        for existing in self._criteria.values():
            if existing.name.lower() == criterion.name.lower():
                raise DomainError(f"Критерий «{criterion.name}» уже есть в рубрикаторе")
        self._criteria[criterion.id] = criterion

    def remove_criterion(self, criterion_id: str) -> None:
        if criterion_id not in self._criteria:
            raise DomainError("Такого критерия нет в рубрикаторе")
        del self._criteria[criterion_id]

    def has(self, criterion_id: str) -> bool:
        return criterion_id in self._criteria

    def get(self, criterion_id: str) -> Criterion:
        if criterion_id not in self._criteria:
            raise DomainError("Такого критерия нет в рубрикаторе")
        return self._criteria[criterion_id]

    def criteria(self) -> list[Criterion]:
        return list(self._criteria.values())

    def is_empty(self) -> bool:
        return len(self._criteria) == 0


class RubricBuilder:
    """Builder: рубрикатор собирается по шагам, а build() проверяет, что получилось целое.

    Используется при загрузке рубрикатора из файла и в демо-сценарии:
    если хоть один критерий кривой (или файл испорчен), рубрикатор не соберётся.
    """

    def __init__(self):
        self._items: list[tuple[str, float, float, str | None]] = []

    def add(self, name: str, max_score: float, weight: float, criterion_id: str | None = None) -> "RubricBuilder":
        self._items.append((name, max_score, weight, criterion_id))
        return self

    def build(self, allow_empty: bool = False) -> Rubric:
        if not self._items and not allow_empty:
            raise DomainError("Рубрикатор должен содержать хотя бы один критерий")
        rubric = Rubric()
        for name, max_score, weight, criterion_id in self._items:
            # конструктор Criterion и add_criterion сами проверяют значения и дубликаты
            rubric.add_criterion(Criterion(name, max_score, weight, criterion_id))
        return rubric
