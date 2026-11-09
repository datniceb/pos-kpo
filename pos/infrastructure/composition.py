import os

from pos.application.facade import PosFacade
from pos.application.ports import ResultExporter
from pos.domain.grading import (
    FinalGradeCalculator,
    GradedOnlyWeightedAverage,
    RoundingDecorator,
    StrictWeightedAverage,
)
from pos.domain.ports import RubricRepository, StudentRepository
from pos.infrastructure.container import Container
from pos.infrastructure.csv_exporter import CsvResultExporter
from pos.infrastructure.json_repositories import JsonRubricRepository, JsonStudentRepository
from pos.infrastructure.memory_repositories import InMemoryRubricRepository, InMemoryStudentRepository

STRATEGIES = "strategies"


def build_container(data_dir: str = "data", in_memory: bool = False) -> Container:
    """Composition root: единственное место, где выбираются конкретные реализации."""
    c = Container()

    if in_memory:
        c.register(RubricRepository, lambda c: InMemoryRubricRepository())
        c.register(StudentRepository, lambda c: InMemoryStudentRepository())
    else:
        c.register(RubricRepository, lambda c: JsonRubricRepository(os.path.join(data_dir, "rubric.json")))
        c.register(
            StudentRepository,
            lambda c: JsonStudentRepository(os.path.join(data_dir, "students.json"), c.resolve(RubricRepository)),
        )

    c.register(ResultExporter, lambda c: CsvResultExporter())
    c.register(FinalGradeCalculator, lambda c: FinalGradeCalculator())
    c.register(
        STRATEGIES,
        lambda c: {
            "final": RoundingDecorator(StrictWeightedAverage(), digits=0),
            "strict": RoundingDecorator(StrictWeightedAverage(), digits=2),
            "intermediate": RoundingDecorator(GradedOnlyWeightedAverage(), digits=2),
        },
    )
    c.register(
        PosFacade,
        lambda c: PosFacade(
            c.resolve(StudentRepository),
            c.resolve(RubricRepository),
            c.resolve(FinalGradeCalculator),
            c.resolve(STRATEGIES),
            c.resolve(ResultExporter),
        ),
    )
    return c
