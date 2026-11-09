from pos.application.facade import NotFoundError, PosFacade
from pos.domain.errors import DomainError
from pos.infrastructure.json_repositories import StorageError

MENU = """
========== ПОС: преподавательская оценка студентов ==========
 1. Добавить студента
 2. Список студентов
 3. Добавить критерий
 4. Показать рубрикатор
 5. Удалить критерий
 6. Выставить / исправить оценку
 7. Оценки студента
 8. Отменить оценку
 9. Итог студента
10. Итоги всех студентов
11. Экспорт итогов в CSV
 0. Выход
"""


class ConsoleApp:
    """Входящий адаптер: читает ввод, вызывает фасад, печатает результат.

    Доменных правил здесь нет — только разбор ввода и перехват ошибок,
    чтобы программа не падала от «abc» вместо числа.
    """

    def __init__(self, facade: PosFacade):
        self._facade = facade
        self._actions = {
            "1": self.add_student,
            "2": self.show_students,
            "3": self.add_criterion,
            "4": self.show_rubric,
            "5": self.remove_criterion,
            "6": self.set_evaluation,
            "7": self.show_evaluations,
            "8": self.cancel_evaluation,
            "9": self.show_final_grade,
            "10": self.show_all_final_grades,
            "11": self.export,
        }

    def run(self) -> None:
        while True:
            print(MENU)
            try:
                choice = input("Выберите пункт: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nДо свидания!")
                return
            if choice == "0":
                print("До свидания!")
                return
            action = self._actions.get(choice)
            if action is None:
                print("Нет такого пункта меню.")
                continue
            try:
                action()
            except DomainError as e:
                print(f"Ошибка: {e}")
            except NotFoundError as e:
                print(f"Не найдено: {e}")
            except StorageError as e:
                print(f"Проблема с файлом данных: {e}")
            except OSError as e:
                print(f"Не удалось записать файл: {e}")
            except (EOFError, KeyboardInterrupt):
                print("\nДо свидания!")
                return
            except Exception as e:  # последний рубеж: что бы ни случилось, программа не падает
                print(f"Непредвиденная ошибка: {e}")

    # ---------- сценарии ----------

    def add_student(self) -> None:
        name = input("Имя студента: ")
        student = self._facade.add_student(name)
        print(f"Студент «{student.name}» добавлен (id {student.id}).")

    def show_students(self) -> None:
        students = self._facade.list_students()
        if not students:
            print("Студентов пока нет.")
            return
        for i, s in enumerate(students, start=1):
            print(f"{i}. {s.name} (id {s.id})")

    def add_criterion(self) -> None:
        name = input("Название критерия: ")
        max_score = self._ask_number("Максимальный балл: ")
        weight = self._ask_number("Вес в итоге: ")
        criterion = self._facade.add_criterion(name, max_score, weight)
        print(f"Критерий «{criterion.name}» добавлен.")

    def show_rubric(self) -> None:
        criteria = self._facade.list_criteria()
        if not criteria:
            print("Рубрикатор пуст.")
            return
        for i, c in enumerate(criteria, start=1):
            print(f"{i}. {c.name}: максимум {c.max_score:g}, вес {c.weight:g}")

    def remove_criterion(self) -> None:
        criterion = self._choose_criterion()
        if criterion is None:
            return
        count = self._facade.count_evaluations_for(criterion.id)
        if count > 0:
            answer = input(f"По этому критерию есть оценки у {count} студ. Удалить вместе с ними? (да/нет): ")
            if answer.strip().lower() not in ("да", "д", "y", "yes"):
                print("Удаление отменено.")
                return
        self._facade.remove_criterion(criterion.id)
        print(f"Критерий «{criterion.name}» удалён.")

    def set_evaluation(self) -> None:
        student = self._choose_student()
        if student is None:
            return
        criterion = self._choose_criterion()
        if criterion is None:
            return
        score = self._ask_number(f"Балл (от 0 до {criterion.max_score:g}): ")
        comment = input("Комментарий (можно пусто): ")
        corrected = self._facade.set_evaluation(student.id, criterion.id, score, comment)
        if corrected:
            print("Оценка исправлена.")
        else:
            print("Оценка выставлена.")

    def show_evaluations(self) -> None:
        student = self._choose_student()
        if student is None:
            return
        evaluations = self._facade.student_evaluations(student.id)
        if not evaluations:
            print("У студента пока нет оценок.")
            return
        for e in evaluations:
            line = f"- {e.criterion.name}: {e.score:g} из {e.criterion.max_score:g} ({e.created.isoformat()})"
            if e.comment:
                line += f" — {e.comment}"
            print(line)

    def cancel_evaluation(self) -> None:
        student = self._choose_student()
        if student is None:
            return
        criterion = self._choose_criterion()
        if criterion is None:
            return
        self._facade.cancel_evaluation(student.id, criterion.id)
        print("Оценка отменена.")

    def show_final_grade(self) -> None:
        student = self._choose_student()
        if student is None:
            return
        strategy = self._choose_strategy()
        grade = self._facade.final_grade(student.id, strategy)
        print(f"Итог студента {student.name}: {grade:g}")

    def show_all_final_grades(self) -> None:
        strategy = self._choose_strategy()
        grades = self._facade.final_grades(strategy)
        if not grades:
            print("Студентов пока нет.")
            return
        for student, grade in grades:
            print(f"{student.name} (id {student.id}): {grade:g}")

    def export(self) -> None:
        strategy = self._choose_strategy()
        path = input("Имя файла [results.csv]: ").strip() or "results.csv"
        count = self._facade.export_final_grades(path, strategy)
        print(f"Выгружено студентов: {count}. Файл: {path}")

    # ---------- разбор ввода ----------

    @staticmethod
    def _ask_number(prompt: str) -> float:
        while True:
            text = input(prompt).strip().replace(",", ".")
            try:
                return float(text)
            except ValueError:
                print("Нужно ввести число, например 7 или 7.5")

    @staticmethod
    def _ask_index(count: int) -> int | None:
        """Спрашивает номер из списка от 1 до count. Пустой ввод — отмена."""
        while True:
            text = input("Номер (Enter — отмена): ").strip()
            if text == "":
                return None
            if text.isdecimal() and 1 <= int(text) <= count:
                return int(text) - 1
            print(f"Введите номер от 1 до {count}")

    def _choose_student(self):
        students = self._facade.list_students()
        if not students:
            print("Сначала добавьте студентов.")
            return None
        print("Студенты:")
        for i, s in enumerate(students, start=1):
            print(f"{i}. {s.name} (id {s.id})")
        index = self._ask_index(len(students))
        return None if index is None else students[index]

    def _choose_criterion(self):
        criteria = self._facade.list_criteria()
        if not criteria:
            print("Сначала добавьте критерии.")
            return None
        print("Критерии:")
        for i, c in enumerate(criteria, start=1):
            print(f"{i}. {c.name} (максимум {c.max_score:g}, вес {c.weight:g})")
        index = self._ask_index(len(criteria))
        return None if index is None else criteria[index]

    def _choose_strategy(self) -> str:
        strategies = list(self._facade.strategies().items())
        print("Как считать итог:")
        for i, (_, title) in enumerate(strategies, start=1):
            print(f"{i}. {title}")
        while True:
            text = input("Номер [1]: ").strip()
            if text == "":
                return strategies[0][0]
            if text.isdecimal() and 1 <= int(text) <= len(strategies):
                return strategies[int(text) - 1][0]
            print(f"Введите номер от 1 до {len(strategies)}")
