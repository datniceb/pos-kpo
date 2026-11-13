class Container:
    """Простой DI-контейнер.

    register(ключ, провайдер) — запомнить, как создать объект;
    resolve(ключ) — создать объект (один раз) и вернуть его.
    Ключом служит абстракция (порт), поэтому код просит «StudentRepository»,
    а какая реализация придёт, решает только composition root.
    """

    def __init__(self):
        self._providers = {}
        self._instances = {}

    def register(self, key, provider) -> None:
        self._providers[key] = provider
        self._instances.pop(key, None)

    def resolve(self, key):
        if key not in self._instances:
            if key not in self._providers:
                raise KeyError(f"В контейнере ничего не зарегистрировано для {key}")
            self._instances[key] = self._providers[key](self)
        return self._instances[key]
