from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from collections import defaultdict


class ContextStorage(ABC):

    def __init__(self, namespace_elements:tuple):
        self.namespace = ':'.join(namespace_elements)

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass


class InMemoryContextStorage(ContextStorage):
    data = defaultdict(lambda: defaultdict(None))
    
    def __init__(self, namespace:tuple):
        super().__init__(namespace)
        

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        namespace_data = InMemoryContextStorage.data.get(self.namespace, None)
        if namespace_data is None:
            return None
        return namespace_data.get(key, None)

    def set(self, key: str, value: Any) -> None:
        InMemoryContextStorage.data[self.namespace][key] = value

    def delete(self, key: str) -> None:
        del InMemoryContextStorage.data[self.namespace][key]