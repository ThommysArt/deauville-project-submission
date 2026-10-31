import copy
import json
from abc import ABC, abstractmethod
from pathlib import Path

from .errors import StorageError


class Storage(ABC):
    @abstractmethod
    def load(self) -> dict: ...

    @abstractmethod
    def save(self, data: dict) -> None: ...


class JsonStorage(Storage):
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise StorageError(f"Data file not found: {self.path}.") from None
        except json.JSONDecodeError as error:
            raise StorageError(f"Data file {self.path} is damaged: {error}.") from None
        except OSError as error:
            raise StorageError(f"Cannot read {self.path}: {error}.") from None

    def save(self, data: dict) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(temporary, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary.replace(self.path)
        except OSError as error:
            raise StorageError(f"Cannot write {self.path}: {error}.") from None


class MemoryStorage(Storage):
    def __init__(self, data: dict) -> None:
        self._data = copy.deepcopy(data)

    def load(self) -> dict:
        return copy.deepcopy(self._data)

    def save(self, data: dict) -> None:
        self._data = copy.deepcopy(data)
