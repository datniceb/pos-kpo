import csv
import json

import pytest

from pos.application.facade import NotFoundError, PosFacade
from pos.domain.errors import DomainError
from pos.infrastructure.composition import build_container
from pos.infrastructure.json_repositories import StorageError


@pytest.fixture
def facade() -> PosFacade:
    return build_container(in_memory=True).resolve(PosFacade)


def test_remove_criterion_removes_its_evaluations(facade):
    hw = facade.add_criterion("ДЗ", 10, 1)
    exam = facade.add_criterion("Экзамен", 10, 1)
    student = facade.add_student("Иванов")
    facade.set_evaluation(student.id, hw.id, 8)
    facade.set_evaluation(student.id, exam.id, 6)

    affected = facade.remove_criterion(hw.id)

    assert affected == 1
    evaluations = facade.student_evaluations(student.id)
    assert [e.criterion.id for e in evaluations] == [exam.id]


def test_unknown_student(facade):
    hw = facade.add_criterion("ДЗ", 10, 1)
    with pytest.raises(NotFoundError):
        facade.set_evaluation("нет-такого", hw.id, 5)


def test_out_of_range_through_facade(facade):
    hw = facade.add_criterion("ДЗ", 10, 1)
    student = facade.add_student("Иванов")
    with pytest.raises(DomainError):
        facade.set_evaluation(student.id, hw.id, 12)
    assert facade.student_evaluations(student.id) == []


def test_export_writes_csv(facade, tmp_path):
    hw = facade.add_criterion("ДЗ", 10, 1)
    student = facade.add_student("Иванов")
    facade.set_evaluation(student.id, hw.id, 8)
    path = tmp_path / "out.csv"

    facade.export_final_grades(str(path), "final")

    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    assert rows == [["ID", "Студент", "Итог"], [student.id, "Иванов", "8"]]


def test_json_storage_keeps_data_between_runs(tmp_path):
    first = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    hw = first.add_criterion("ДЗ", 10, 1)
    student = first.add_student("Иванов")
    first.set_evaluation(student.id, hw.id, 7.5, "норм")

    # «перезапуск программы» — новый контейнер поверх тех же файлов
    second = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    evaluations = second.student_evaluations(student.id)
    assert len(evaluations) == 1
    assert evaluations[0].score == 7.5
    assert evaluations[0].comment == "норм"
    assert second.final_grade(student.id, "strict") == 7.5


def test_broken_json_file(tmp_path):
    (tmp_path / "rubric.json").write_text("{ это не json", encoding="utf-8")
    facade = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    with pytest.raises(StorageError):
        facade.list_criteria()


def test_json_file_not_in_utf8(tmp_path):
    (tmp_path / "rubric.json").write_bytes(b"\xff\xfe\x00garbage")
    facade = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    with pytest.raises(StorageError):
        facade.list_criteria()


def test_json_file_with_wrong_types(tmp_path):
    (tmp_path / "rubric.json").write_text(
        json.dumps({"criteria": [{"id": "a", "name": 123, "max_score": 10, "weight": 1}]}),
        encoding="utf-8",
    )
    facade = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    with pytest.raises(StorageError):
        facade.list_criteria()


def test_json_file_with_score_above_max(tmp_path):
    (tmp_path / "rubric.json").write_text(
        json.dumps({"criteria": [{"id": "hw", "name": "ДЗ", "max_score": 10, "weight": 1}]}),
        encoding="utf-8",
    )
    (tmp_path / "students.json").write_text(
        json.dumps(
            {
                "students": [
                    {
                        "id": "s1",
                        "name": "Иванов",
                        "evaluations": [{"criterion_id": "hw", "score": 99, "comment": "", "date": "2026-11-09"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    facade = build_container(data_dir=str(tmp_path)).resolve(PosFacade)
    with pytest.raises(StorageError):
        facade.list_students()
