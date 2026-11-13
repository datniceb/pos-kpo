from pos.application.ports import ResultExporter
from pos.domain.criterion import Criterion
from pos.domain.evaluation import Evaluation, EvaluationFactory
from pos.domain.grading import FinalGradeCalculator, GradingStrategy
from pos.domain.ports import RubricRepository, StudentRepository
from pos.domain.student import Student


class NotFoundError(Exception):
    """Запрошенный объект не найден (это не нарушение домена, а ошибка сценария)."""


class PosFacade:
    """Facade: единая точка входа для консоли. Каждый метод — один сценарий (use case).

    Консоль не знает про репозитории, фабрику и доменный сервис — только про этот класс.
    Сам фасад правил не проверяет: достаёт объекты, вызывает домен и сохраняет результат.
    """

    def __init__(
        self,
        students: StudentRepository,
        rubrics: RubricRepository,
        calculator: FinalGradeCalculator,
        strategies: dict[str, GradingStrategy],
        exporter: ResultExporter,
    ):
        self._students = students
        self._rubrics = rubrics
        self._calculator = calculator
        self._strategies = strategies
        self._exporter = exporter

    # ---------- студенты ----------

    def add_student(self, name: str) -> Student:
        student = Student(name)
        self._students.save(student)
        return student

    def list_students(self) -> list[Student]:
        return self._students.list_all()

    # ---------- рубрикатор ----------

    def add_criterion(self, name: str, max_score: float, weight: float) -> Criterion:
        rubric = self._rubrics.get()
        criterion = Criterion(name, max_score, weight)
        rubric.add_criterion(criterion)
        self._rubrics.save(rubric)
        return criterion

    def list_criteria(self) -> list[Criterion]:
        return self._rubrics.get().criteria()

    def count_evaluations_for(self, criterion_id: str) -> int:
        count = 0
        for student in self._students.list_all():
            if student.evaluation_for(criterion_id) is not None:
                count += 1
        return count

    def remove_criterion(self, criterion_id: str) -> int:
        """Удаляет критерий вместе со всеми оценками по нему. Возвращает, у скольких студентов они были."""
        rubric = self._rubrics.get()
        rubric.remove_criterion(criterion_id)
        affected = 0
        for student in self._students.list_all():
            if student.evaluation_for(criterion_id) is not None:
                student.remove_evaluations_for(criterion_id)
                self._students.save(student)
                affected += 1
        self._rubrics.save(rubric)
        return affected

    # ---------- оценки ----------

    def set_evaluation(self, student_id: str, criterion_id: str, score: float, comment: str = "") -> bool:
        """Выставляет оценку. Если оценка по критерию уже была — исправляет. Возвращает True, если это исправление."""
        student = self._get_student(student_id)
        rubric = self._rubrics.get()
        evaluation = EvaluationFactory(rubric).create(criterion_id, score, comment)
        was_corrected = student.evaluation_for(criterion_id) is not None
        student.put_evaluation(evaluation, rubric)
        self._students.save(student)
        return was_corrected

    def cancel_evaluation(self, student_id: str, criterion_id: str) -> None:
        student = self._get_student(student_id)
        student.cancel_evaluation(criterion_id)
        self._students.save(student)

    def student_evaluations(self, student_id: str) -> list[Evaluation]:
        return self._get_student(student_id).evaluations()

    # ---------- итог ----------

    def strategies(self) -> dict[str, str]:
        """Ключ стратегии -> понятное название для меню."""
        return {key: strategy.name for key, strategy in self._strategies.items()}

    def final_grade(self, student_id: str, strategy_key: str) -> float:
        student = self._get_student(student_id)
        return self._calculator.calculate(student, self._rubrics.get(), self._get_strategy(strategy_key))

    def final_grades(self, strategy_key: str) -> list[tuple[Student, float]]:
        rubric = self._rubrics.get()
        strategy = self._get_strategy(strategy_key)
        result = []
        for student in self._students.list_all():
            result.append((student, self._calculator.calculate(student, rubric, strategy)))
        return result

    def export_final_grades(self, path: str, strategy_key: str) -> int:
        grades = self.final_grades(strategy_key)
        rows = [(student.id, student.name, grade) for student, grade in grades]
        self._exporter.export(rows, path)
        return len(rows)

    # ---------- вспомогательное ----------

    def _get_student(self, student_id: str) -> Student:
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError("Студент не найден")
        return student

    def _get_strategy(self, key: str) -> GradingStrategy:
        if key not in self._strategies:
            raise NotFoundError(f"Неизвестное правило подсчёта итога: {key}")
        return self._strategies[key]
