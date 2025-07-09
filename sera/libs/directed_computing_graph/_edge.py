from __future__ import annotations

from typing import Annotated, Any, Callable, Optional

from graph.interface import BaseEdge

from sera.libs.directed_computing_graph._node import NodeId
from sera.libs.directed_computing_graph._type_conversion import UnitTypeConversion


class DCGEdge(BaseEdge[NodeId, int]):

    def __init__(
        self,
        id: int,
        source: NodeId,
        target: NodeId,
        argindex: int,
        type_conversion: UnitTypeConversion,
        filter_fn: Optional[Callable[[Any], bool]] = None,
    ):
        super().__init__(id, source, target, key=argindex)
        self.argindex = argindex
        self.type_conversion = type_conversion
        self.filter_fn = filter_fn

    def filter(self, value: Any) -> bool:
        """Filter the value passing through this edge.

        Returns:
            True if the value should flow through this edge, False to block it.
        """
        if self.filter_fn is not None:
            return self.filter_fn(value)
        return True
