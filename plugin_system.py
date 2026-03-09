import abc
from typing import Any


class BasePlugin(abc.ABC):
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abc.abstractmethod
    def execute(self, data: Any, config: Any) -> Any:
        pass


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin):
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str) -> BasePlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())

    def run_plugin(self, name: str, data: Any, config: Any) -> Any:
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.execute(data, config)
        raise ValueError(f"Plugin {name} not found")
