"""Сквозной сценарий из ТЗ: студенты и критерии -> оценки -> итог -> экспорт.

Работает на in-memory хранилище, чтобы не трогать настоящие данные в data/.
"""

from pos.application.facade import PosFacade
from pos.domain.errors import DomainError
from pos.infrastructure.composition import build_container

facade = build_container(in_memory=True).resolve(PosFacade)

print("1) Заводим критерии")
hw = facade.add_criterion("Домашние задания", 10, 0.4)
cw = facade.add_criterion("Контрольная", 10, 0.2)
exam = facade.add_criterion("Экзамен", 10, 0.4)
for c in facade.list_criteria():
    print(f"   {c.name}: максимум {c.max_score:g}, вес {c.weight:g}")

print("2) Заводим студентов")
ivanov = facade.add_student("Иванов Иван")
petrova = facade.add_student("Петрова Мария")
sidorov = facade.add_student("Сидоров Пётр")
for s in facade.list_students():
    print(f"   {s.name}")

print("3) Выставляем оценки")
facade.set_evaluation(ivanov.id, hw.id, 8, "сдал всё вовремя")
facade.set_evaluation(ivanov.id, cw.id, 6.5)
facade.set_evaluation(ivanov.id, exam.id, 7)
facade.set_evaluation(petrova.id, hw.id, 10)
facade.set_evaluation(petrova.id, cw.id, 9)
facade.set_evaluation(petrova.id, exam.id, 8.5)
facade.set_evaluation(sidorov.id, hw.id, 9)  # контрольную и экзамен ещё не сдавал
print("   готово")

print("4) Исправляем оценку: у Иванова за контрольную было 6.5, ставим 7")
corrected = facade.set_evaluation(ivanov.id, cw.id, 7)
print(f"   это исправление: {corrected}")

print("5) Пробуем нарушить правила домена")
try:
    facade.set_evaluation(ivanov.id, exam.id, 12)
except DomainError as e:
    print(f"   не дали: {e}")
try:
    facade.set_evaluation(ivanov.id, "нет-такого", 5)
except DomainError as e:
    print(f"   не дали: {e}")

print("6) Итоги по разным правилам (Strategy)")
for key, title in facade.strategies().items():
    print(f"   [{title}]")
    for student, grade in facade.final_grades(key):
        print(f"      {student.name}: {grade:g}")

print("7) Экспорт финальных итогов")
count = facade.export_final_grades("demo_results.csv", "final")
print(f"   выгружено {count} студентов в demo_results.csv")
