from pos.application.facade import PosFacade
from pos.infrastructure.composition import build_container
from pos.infrastructure.console import ConsoleApp

# composition root: контейнер собирает граф объектов, дальше работает консоль
container = build_container(data_dir="data")
ConsoleApp(container.resolve(PosFacade)).run()
