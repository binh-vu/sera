from __future__ import annotations

from dataclasses import dataclass
from graphlib import TopologicalSorter

from sera.models._class import Class
from sera.models._enum import Enum
from sera.models._property import ObjectProperty


@dataclass
class Schema:
    # top-level application name
    name: str
    classes: dict[str, Class]
    enums: dict[str, Enum]

    def topological_sort(self) -> list[Class]:
        """
        Sort classes in topological order using graphlib.TopologicalSorter.
        """
        # Build the dependency graph
        graph = {}
        for cls_name, cls in self.classes.items():
            dependencies = set()
            for prop in cls.properties.values():
                if isinstance(prop, ObjectProperty) and prop.target.name != cls_name:
                    dependencies.add(prop.target.name)
            graph[cls_name] = dependencies

        # Create topological sorter and get sorted class names
        sorter = TopologicalSorter(graph)
        sorted_names = list(sorter.static_order())

        # Convert sorted names back to Class objects
        return [self.classes[name] for name in sorted_names]

    def get_upstream_classes(self, cls: Class) -> list[tuple[Class, ObjectProperty]]:
        """
        Get all classes that depend on the given class.
        """
        upstream_classes = []
        for other_cls in self.classes.values():
            for prop in other_cls.properties.values():
                if isinstance(prop, ObjectProperty) and prop.target.name == cls.name:
                    upstream_classes.append((other_cls, prop))
        return upstream_classes
