from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Callable

from graph.interface import BaseNode

from sera.libs.directed_computing_graph._fn_signature import FnSignature
from sera.libs.directed_computing_graph._type_conversion import UnitTypeConversion


class PartialFn:
    def __init__(self, fn: Callable, **kwargs):
        self.fn = fn
        self.default_args = kwargs
        self.signature = FnSignature.parse(fn)

        argnames = set(self.signature.argnames)
        for arg, val in self.default_args.items():
            if arg not in argnames:
                raise Exception(f"Argument {arg} is not in the function signature")
            self.signature.default_args[arg] = val

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


ComputeFnId = Annotated[str, "ComputeFn Identifier"]
ComputeFn = PartialFn | Callable
NodeId = ComputeFnId


class DCGNode(BaseNode[NodeId]):
    id: NodeId
    func: ComputeFn

    def __init__(self, id: NodeId, func: ComputeFn):
        super().__init__(id)
        self.func = func
        self.signature = self.get_signature(self.func)
        self.type_conversions: list[UnitTypeConversion] = []
        self.required_args: list[str] = []
        self.required_context: list[str] = []
        self.required_context_default_args: dict[str, Any] = {}

    @staticmethod
    def get_signature(actor: ComputeFn) -> FnSignature:
        if isinstance(actor, PartialFn):
            return actor.signature
        else:
            return FnSignature.parse(actor)
