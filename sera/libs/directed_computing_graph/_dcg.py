from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from enum import Enum
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    MutableSequence,
    Optional,
    Sequence,
)

from graph.retworkx import RetworkXStrDiGraph

from sera.libs.directed_computing_graph._edge import DCGEdge
from sera.libs.directed_computing_graph._flow import Flow
from sera.libs.directed_computing_graph._node import (
    ComputeFn,
    ComputeFnId,
    DCGNode,
    NodeId,
)
from sera.libs.directed_computing_graph._runtime import SKIP, NodeRuntime
from sera.libs.directed_computing_graph._type_conversion import (
    ComposeTypeConversion,
    TypeConversion,
    UnitTypeConversion,
    align_generic_type,
    ground_generic_type,
    is_generic_type,
)
from sera.misc import identity

TaskKey = Annotated[tuple, "TaskKey"]
TaskArgs = Annotated[MutableSequence, "TaskArgs"]


class DirectedComputingGraph:
    """
    A Directed Computing Graph (DCG) is a directed graph where nodes represent functions
    and edges represent dependencies between these functions. The graph is used to manage
    the execution of functions in a specific order based on their dependencies.
    """

    def __init__(
        self,
        graph: RetworkXStrDiGraph[int, DCGNode, DCGEdge],
        type_service: TypeConversion,
    ):
        self.graph = graph
        self.type_service = type_service

    @staticmethod
    def from_flows(
        flows: dict[ComputeFnId, Flow | ComputeFn],
        type_conversions: Optional[
            Sequence[UnitTypeConversion | ComposeTypeConversion]
        ] = None,
        strict: bool = True,
    ):
        """Create a computing graph from flow mapping.

        Args:
            flows: A dictionary mapping identifier to:
                1. a function
                2. a flow specifying the upstream functions and the function.
            type_conversions: A list of type conversions to be used for converting the input types.
            strict: If True, we do type checking.
        Returns:
            DirectedComputingGraph: A directed computing graph constructed from the provided flows.
        """
        # add typing conversions
        upd_type_conversions: list[UnitTypeConversion | ComposeTypeConversion] = list(
            type_conversions or []
        )
        type_service = TypeConversion(upd_type_conversions)

        g: RetworkXStrDiGraph[int, DCGNode, DCGEdge] = RetworkXStrDiGraph(
            check_cycle=False, multigraph=False
        )

        # create a graph
        for uid, uinfo in flows.items():
            if isinstance(uinfo, Flow):
                actor = uinfo.target
            else:
                actor = uinfo
            g.add_node(DCGNode(uid, actor))

        # create a graph
        for uid, uinfo in flows.items():
            if isinstance(uinfo, Flow):
                func = uinfo.target
            else:
                func = uinfo
            g.add_node(DCGNode(uid, func))

        # grounding function that has generic type input and output
        for uid, flow in flows.items():
            if not isinstance(flow, Flow):
                continue

            u = g.get_node(uid)
            usig = u.signature
            if is_generic_type(usig.return_type) or any(
                is_generic_type(t) for t in usig.argtypes
            ):
                var2type = {}
                for i, t in enumerate(usig.argtypes):
                    if is_generic_type(t):
                        # align the generic type with the previous return type
                        if len(flow.source) <= i and strict:
                            raise TypeConversion.UnknownConversion(
                                f"Cannot ground the generic type based on upstream actors for actor {uid}"
                            )

                        source_return_type = g.get_node(
                            flow.source[i]
                        ).signature.return_type

                        try:
                            usig.argtypes[i], (var, nt) = align_generic_type(
                                t, source_return_type
                            )
                        except Exception as e:
                            raise TypeConversion.UnknownConversion(
                                f"Cannot align the generic type {t} based on upstream actors for actor {uid}"
                            )
                        var2type[var] = nt
                if is_generic_type(usig.return_type):
                    usig.return_type = ground_generic_type(
                        usig.return_type,
                        var2type,
                    )

        for uid, flow in flows.items():
            if not isinstance(flow, Flow):
                continue

            u = g.get_node(uid)
            usig = u.signature
            for idx, sid in enumerate(flow.source):
                s = g.get_node(sid)
                ssig = s.signature
                cast_fn = identity
                try:
                    cast_fn = type_service.get_conversion(
                        ssig.return_type, usig.argtypes[idx]
                    )
                except Exception as e:
                    if strict:
                        raise TypeConversion.UnknownConversion(
                            f"Don't know how to convert output of `{sid}` to input of `{uid}`"
                        ) from e
                g.add_edge(
                    DCGEdge(
                        id=-1,
                        source=sid,
                        target=uid,
                        argindex=idx,
                        filter_fn=flow.filter_fn,
                        type_conversion=cast_fn,
                    )
                )

        # postprocessing such as type conversion, and args/context
        for u in g.iter_nodes():
            inedges = g.in_edges(u.id)

            # update the type conversion
            u.type_conversions = [identity] * len(u.signature.argnames)
            for inedge in inedges:
                u.type_conversions[inedge.argindex] = inedge.type_conversion

            # update the required args and context
            u.required_args = u.signature.argnames[: g.in_degree(u.id)]
            # arguments of a compute function that are not provided by the upstream actors must be provided by the context.
            u.required_context = u.signature.argnames[g.in_degree(u.id) :]
            u.required_context_default_args = {
                k: u.signature.default_args[k]
                for k in u.required_context
                if k in u.signature.default_args
            }

        return DirectedComputingGraph(g, type_service)

    def execute(
        self,
        input: dict[ComputeFnId, tuple],
        output: set[str],
        context: Optional[
            dict[str, Callable | Any] | Callable[[], dict[str, Any]]
        ] = None,
    ):
        """
        Execute the directed computing graph with the given input and output specifications.

        Args:
            input: A dictionary mapping function identifiers to their input arguments.
            output: A set of function identifiers that should be executed.
            context: An optional context that can be a dictionary of functions or a single function.
        """
        assert all(
            isinstance(v, tuple) for v in input.values()
        ), "Input must be a tuple"

        if context is None:
            context = {}
        elif isinstance(context, Callable):
            context = context()
        else:
            context = {k: v() if callable(v) else v for k, v in context.items()}

        # This is a quick reactive algorithm, we may be able to do it better.
        # The idea is when all inputs of a function is available, we can execute a function.
        # We assume that the memory is large enough to hold all the functions and their inputs
        # in the memory.

        # we execute the computing nodes
        # when it's finished, we put the outgoing edges into a stack.
        runtimes: dict[NodeId, NodeRuntime] = {}

        for u in self.graph.iter_nodes():
            if u.id in input:
                # user provided input should supersede the context
                n_provided_args = len(input[u.id])
                n_consumed_context = n_provided_args - len(u.required_args)
            else:
                n_consumed_context = 0

            node_context = tuple(
                (
                    context[name]
                    if name in context
                    else u.required_context_default_args[name]
                )
                for name in u.required_context[n_consumed_context:]
            )

            runtimes[u.id] = NodeRuntime.from_node(self.graph, u, node_context)
        stack: list[NodeId] = []

        for id, args in input.items():
            runtimes[id].add_task((0,), list(args))
            stack.append(id)

        return_output = {id: [] for id in output}

        while len(stack) > 0:
            # pop the one from the stack and execute it.
            id = stack.pop()
            runtime = runtimes[id]

            # if there is enough data for the node, we can execute it.
            # if it is not, we just skip it and it will be added back to the stack by one of its parents.
            # so we don't miss it.
            if not runtime.has_enough_data():
                continue

            outedges = self.graph.out_edges(id)
            successors: Sequence[tuple[DCGEdge, DCGNode]] = [
                (edge, self.graph.get_node(edge.target)) for edge in outedges
            ]

            # run the tasks and pass the output to the successors
            for task_id, task in runtime.tasks.items():
                if any(arg is SKIP for arg in task):
                    task_output = SKIP
                else:
                    task_output = runtime.execute(task)

                for outedge, succ in successors:
                    runtimes[succ.id].add_task_args(
                        task_id,
                        id,
                        (
                            SKIP
                            if task_output is SKIP or not outedge.filter(task_output)
                            else task_output
                        ),
                    )

                if id in output and task_output is not SKIP:
                    return_output[id].append(task_output)

            # retrieve the outgoing nodes and push them into the stack
            for outedge, succ in successors:
                stack.append(succ.id)

        return return_output

    async def execute_async(
        self,
        input: dict[ComputeFnId, tuple],
        output: set[str],
        context: Optional[
            dict[str, Callable | Any] | Callable[[], dict[str, Any]]
        ] = None,
    ):
        """
        Asynchronously execute the directed computing graph with the given input and output specifications.
        This method handles both synchronous and asynchronous functions.

        Args:
            input: A dictionary mapping function identifiers to their input arguments.
            output: A set of function identifiers that should be executed.
            context: An optional context that can be a dictionary of functions or a single function.
        """
        assert all(
            isinstance(v, tuple) for v in input.values()
        ), "Input must be a tuple"

        if context is None:
            context = {}
        elif isinstance(context, Callable):
            context = context()
        else:
            context = {k: v() if callable(v) else v for k, v in context.items()}

        # This is a quick reactive algorithm, we may be able to do it better.
        # The idea is when all inputs of a function is available, we can execute a function.
        # We assume that the memory is large enough to hold all the functions and their inputs
        # in the memory.

        # we execute the computing nodes
        # when it's finished, we put the outgoing edges into a stack.
        runtimes: dict[NodeId, NodeRuntime] = {}

        for u in self.graph.iter_nodes():
            if u.id in input:
                # user provided input should supersede the context
                n_provided_args = len(input[u.id])
                n_consumed_context = n_provided_args - len(u.required_args)
            else:
                n_consumed_context = 0

            node_context = tuple(
                (
                    context[name]
                    if name in context
                    else u.required_context_default_args[name]
                )
                for name in u.required_context[n_consumed_context:]
            )

            runtimes[u.id] = NodeRuntime.from_node(self.graph, u, node_context)
        stack: list[NodeId] = []

        for id, args in input.items():
            runtimes[id].add_task((0,), list(args))
            stack.append(id)

        return_output = {id: [] for id in output}

        while len(stack) > 0:
            # pop the one from the stack and execute it.
            id = stack.pop()
            runtime = runtimes[id]

            # if there is enough data for the node, we can execute it.
            # if it is not, we just skip it and it will be added back to the stack by one of its parents.
            # so we don't miss it.
            if not runtime.has_enough_data():
                continue

            outedges = self.graph.out_edges(id)
            successors: Sequence[tuple[DCGEdge, DCGNode]] = [
                (edge, self.graph.get_node(edge.target)) for edge in outedges
            ]

            # run the tasks and pass the output to the successors
            for task_id, task in runtime.tasks.items():
                if any(arg is SKIP for arg in task):
                    task_output = SKIP
                else:
                    if runtime.node.signature.is_async:
                        task_output = await runtime.execute(task)
                    else:
                        task_output = runtime.execute(task)

                for outedge, succ in successors:
                    runtimes[succ.id].add_task_args(
                        task_id,
                        id,
                        (
                            SKIP
                            if task_output is SKIP or not outedge.filter(task_output)
                            else task_output
                        ),
                    )

                if id in output and task_output is not SKIP:
                    return_output[id].append(task_output)

            # retrieve the outgoing nodes and push them into the stack
            for outedge, succ in successors:
                stack.append(succ.id)

        return return_output
