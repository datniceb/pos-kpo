from dataclasses import dataclass, field
from datetime import date

from pos.domain.criterion import Criterion
from pos.domain.errors import DomainError
from pos.domain.rubric import Rubric


@dataclass(frozen=True)
class Evaluation:
    """Оценка — Value Object.

    Неизменяемая: исправить оценку = заменить её новым объектом.
    Принимает сам объект критерия, поэтому диапазон балла проверяется прямо здесь,
    и создать оценку 12 из 10 нельзя даже в обход фабрики.
    """

    criterion: Criterion
    score: float
    comment: str = ""
    created: date = field(default_factory=date.today)

    def __post_init__(self):
        # запись через not (...) ловит ещё и nan: с ним любое сравнение даёт False
        if not (0 <= self.score <= self.criterion.max_score):
            raise DomainError(
                f"Балл {self.score:g} вне диапазона критерия «{self.criterion.name}» "
                f"(от 0 до {self.criterion.max_score:g})"
            )


class EvaluationFactory:
    """Factory: единая точка создания оценки.

    Проверяет, что критерий есть в рубрикаторе, и достаёт оттуда сам объект критерия.
    Диапазон балла дальше проверит конструктор Evaluation.
    """

    def __init__(self, rubric: Rubric):
        self._rubric = rubric

    def create(self, criterion_id: str, score: float, comment: str = "") -> Evaluation:
        if not self._rubric.has(criterion_id):
            raise DomainError("Нельзя оценить критерий, которого нет в рубрикаторе")
        criterion = self._rubric.get(criterion_id)
        return Evaluation(criterion, float(score), comment.strip())
