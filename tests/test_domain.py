import pytest

from pos.domain.criterion import Criterion
from pos.domain.errors import DomainError
from pos.domain.evaluation import Evaluation, EvaluationFactory
from pos.domain.grading import (
    FinalGradeCalculator,
    GradedOnlyWeightedAverage,
    GradingStrategy,
    RoundingDecorator,
    StrictWeightedAverage,
)
from pos.domain.rubric import Rubric, RubricBuilder
from pos.domain.student import Student


def make_rubric() -> Rubric:
    return RubricBuilder().add("ДЗ", 10, 0.5, "hw").add("Экзамен", 20, 0.5, "exam").build()


# ---------- критерий ----------


@pytest.mark.parametrize("max_score", [0, -5, float("nan"), float("inf")])
def test_criterion_bad_max_score(max_score):
    with pytest.raises(DomainError):
        Criterion("ДЗ", max_score, 1)


@pytest.mark.parametrize("weight", [0, -1, float("nan"), float("inf")])
def test_criterion_bad_weight(weight):
    with pytest.raises(DomainError):
        Criterion("ДЗ", 10, weight)


def test_criterion_empty_name():
    with pytest.raises(DomainError):
        Criterion("   ", 10, 1)


# ---------- оценка ----------


@pytest.mark.parametrize("score", [-0.1, 10.5, 12, float("nan"), float("inf")])
def test_evaluation_score_out_of_range(score):
    criterion = Criterion("ДЗ", 10, 1)
    with pytest.raises(DomainError):
        Evaluation(criterion, score)


@pytest.mark.parametrize("score", [0, 7.5, 10])
def test_evaluation_score_on_borders_is_ok(score):
    criterion = Criterion("ДЗ", 10, 1)
    assert Evaluation(criterion, score).score == score


def test_evaluation_is_value_object():
    criterion = Criterion("ДЗ", 10, 1)
    a = Evaluation(criterion, 8, "ок")
    b = Evaluation(criterion, 8, "ок")
    assert a == b
    with pytest.raises(AttributeError):
        a.score = 9


def test_factory_rejects_criterion_not_in_rubric():
    factory = EvaluationFactory(make_rubric())
    with pytest.raises(DomainError):
        factory.create("нет-такого", 5)


def test_factory_creates_evaluation_with_criterion_from_rubric():
    rubric = make_rubric()
    evaluation = EvaluationFactory(rubric).create("exam", 15)
    assert evaluation.criterion is rubric.get("exam")


def test_student_rejects_evaluation_created_bypassing_factory():
    rubric = make_rubric()
    student = Student("Иванов")
    foreign = Criterion("Чужой критерий", 10, 1)
    with pytest.raises(DomainError):
        student.put_evaluation(Evaluation(foreign, 5), rubric)


def test_second_evaluation_is_correction():
    rubric = make_rubric()
    student = Student("Иванов")
    factory = EvaluationFactory(rubric)
    student.put_evaluation(factory.create("hw", 5), rubric)
    student.put_evaluation(factory.create("hw", 9), rubric)
    assert len(student.evaluations()) == 1
    assert student.evaluation_for("hw").score == 9


def test_cancel_missing_evaluation():
    with pytest.raises(DomainError):
        Student("Иванов").cancel_evaluation("hw")


# ---------- рубрикатор ----------


def test_builder_empty_rubric():
    with pytest.raises(DomainError):
        RubricBuilder().build()


def test_builder_duplicate_names():
    with pytest.raises(DomainError):
        RubricBuilder().add("ДЗ", 10, 1).add("дз", 5, 1).build()


# ---------- итог ----------


def test_strategies_differ_when_some_criteria_not_graded():
    rubric = make_rubric()
    student = Student("Иванов")
    student.put_evaluation(EvaluationFactory(rubric).create("hw", 10), rubric)
    # оценено только ДЗ на максимум, экзамена нет
    assert StrictWeightedAverage().calculate(student, rubric) == pytest.approx(5.0)
    assert GradedOnlyWeightedAverage().calculate(student, rubric) == pytest.approx(10.0)


def test_strict_uses_weights_and_max_scores():
    rubric = make_rubric()
    student = Student("Иванов")
    factory = EvaluationFactory(rubric)
    student.put_evaluation(factory.create("hw", 8), rubric)  # 0.8 от максимума
    student.put_evaluation(factory.create("exam", 10), rubric)  # 0.5 от максимума
    # 10 * (0.5 * 0.8 + 0.5 * 0.5) / 1.0 = 6.5
    assert StrictWeightedAverage().calculate(student, rubric) == pytest.approx(6.5)


def test_no_evaluations_gives_zero():
    rubric = make_rubric()
    student = Student("Иванов")
    assert StrictWeightedAverage().calculate(student, rubric) == 0
    assert GradedOnlyWeightedAverage().calculate(student, rubric) == 0


def test_rounding_decorator_rounds_half_up():
    rubric = make_rubric()
    student = Student("Иванов")
    factory = EvaluationFactory(rubric)
    student.put_evaluation(factory.create("hw", 8), rubric)
    student.put_evaluation(factory.create("exam", 10), rubric)
    # без декоратора 6.5; встроенный round(6.5) дал бы 6
    assert RoundingDecorator(StrictWeightedAverage()).calculate(student, rubric) == 7


def test_final_grade_follows_current_evaluations():
    rubric = make_rubric()
    student = Student("Иванов")
    factory = EvaluationFactory(rubric)
    calculator = FinalGradeCalculator()
    strategy = StrictWeightedAverage()

    student.put_evaluation(factory.create("hw", 10), rubric)
    assert calculator.calculate(student, rubric, strategy) == pytest.approx(5.0)
    student.put_evaluation(factory.create("exam", 20), rubric)
    assert calculator.calculate(student, rubric, strategy) == pytest.approx(10.0)
    student.cancel_evaluation("hw")
    assert calculator.calculate(student, rubric, strategy) == pytest.approx(5.0)


def test_final_grade_with_empty_rubric():
    with pytest.raises(DomainError):
        FinalGradeCalculator().calculate(Student("Иванов"), Rubric(), StrictWeightedAverage())


def test_final_grade_rejects_evaluations_from_other_rubric():
    old_rubric = make_rubric()
    student = Student("Иванов")
    student.put_evaluation(EvaluationFactory(old_rubric).create("hw", 5), old_rubric)
    new_rubric = RubricBuilder().add("Экзамен", 20, 1, "exam").build()  # без «ДЗ»
    with pytest.raises(DomainError):
        FinalGradeCalculator().calculate(student, new_rubric, StrictWeightedAverage())


def test_final_grade_rejects_broken_strategy():
    class BrokenStrategy(GradingStrategy):
        def calculate(self, student, rubric):
            return 11

    with pytest.raises(DomainError):
        FinalGradeCalculator().calculate(Student("Иванов"), make_rubric(), BrokenStrategy())
