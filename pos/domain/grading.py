import math
from abc import ABC, abstractmethod

from pos.domain.errors import DomainError
from pos.domain.rubric import Rubric
from pos.domain.student import Student

MAX_FINAL_GRADE = 10.0


class GradingStrategy(ABC):
    """Strategy: правило подсчёта итога по 10-балльной шкале."""

    name = ""

    @abstractmethod
    def calculate(self, student: Student, rubric: Rubric) -> float: ...


class StrictWeightedAverage(GradingStrategy):
    """Строгий итог: критерий без оценки считается как 0. Для финальной оценки за курс."""

    name = "строгий (нет оценки = 0)"

    def calculate(self, student: Student, rubric: Rubric) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for criterion in rubric.criteria():
            evaluation = student.evaluation_for(criterion.id)
            score = evaluation.score if evaluation is not None else 0.0
            weighted_sum += criterion.weight * score / criterion.max_score
            total_weight += criterion.weight
        if total_weight == 0:
            return 0.0
        return MAX_FINAL_GRADE * weighted_sum / total_weight


class GradedOnlyWeightedAverage(GradingStrategy):
    """Промежуточный итог: учитываются только оценённые критерии. Для статистики посреди курса."""

    name = "промежуточный (только оценённые)"

    def calculate(self, student: Student, rubric: Rubric) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for criterion in rubric.criteria():
            evaluation = student.evaluation_for(criterion.id)
            if evaluation is None:
                continue
            weighted_sum += criterion.weight * evaluation.score / criterion.max_score
            total_weight += criterion.weight
        if total_weight == 0:
            return 0.0
        return MAX_FINAL_GRADE * weighted_sum / total_weight


class RoundingDecorator(GradingStrategy):
    """Decorator: округляет результат любой стратегии, не меняя её код.

    Обычный round() в Python округляет 6.5 до 6 (банковское округление),
    а в ведомостях 6.5 — это 7, поэтому округляем «по-школьному».
    """

    def __init__(self, inner: GradingStrategy, digits: int = 0):
        if digits < 0:
            raise DomainError("Число знаков после запятой не может быть отрицательным")
        self._inner = inner
        self._digits = digits
        if digits == 0:
            self.name = f"{inner.name}, округление до целого"
        else:
            self.name = f"{inner.name}, округление до {digits} знаков"

    def calculate(self, student: Student, rubric: Rubric) -> float:
        value = self._inner.calculate(student, rubric)
        factor = 10**self._digits
        # 1e-9 спасает от ошибок float вроде 6.4999999999 вместо 6.5
        return math.floor(value * factor + 0.5 + 1e-9) / factor


class FinalGradeCalculator:
    """Domain Service: итог зависит и от студента, и от рубрикатора,
    поэтому не принадлежит ни одному из них.

    Итог нигде не хранится — каждый раз считается заново из текущих оценок.
    Сервис отвечает за то, чтобы итог был согласован:
    - считать есть по чему (рубрикатор не пуст);
    - все оценки студента относятся к текущему рубрикатору;
    - какую бы стратегию ни подставили, итог попадает в шкалу от 0 до 10.
    Сама формула — забота стратегии.
    """

    def calculate(self, student: Student, rubric: Rubric, strategy: GradingStrategy) -> float:
        if rubric.is_empty():
            raise DomainError("Нельзя посчитать итог: рубрикатор пуст")
        for evaluation in student.evaluations():
            if not rubric.has(evaluation.criterion.id):
                raise DomainError(
                    f"У студента {student.name} есть оценка по критерию «{evaluation.criterion.name}», "
                    "которого нет в рубрикаторе — итог не согласован с оценками"
                )
        result = strategy.calculate(student, rubric)
        if not (0 <= result <= MAX_FINAL_GRADE):
            raise DomainError(f"Правило подсчёта вернуло {result:g} — это вне шкалы от 0 до {MAX_FINAL_GRADE:g}")
        return result
