from __future__ import annotations

from dataclasses import dataclass
from graphlib import TopologicalSorter

from sera.models._class import Class
from sera.models._property import ObjectProperty


@dataclass
class Schema:
    classes: dict[str, Class]

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
