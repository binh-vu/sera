from __future__ import annotations

from typing import Any, Callable, Optional

from sera.libs.directed_computing_graph._node import ComputeFn, ComputeFnId


class Flow:
    def __init__(
        self,
        source: list[ComputeFnId] | ComputeFnId,
        target: ComputeFn,
        filter_fn: Optional[Callable[[Any], bool]] = None,
    ):
        self.source = [source] if isinstance(source, str) else source
        self.target = target
        self.filter_fn = filter_fn
