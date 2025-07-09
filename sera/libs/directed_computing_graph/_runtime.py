from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, MutableSequence, Sequence

from graph.retworkx import RetworkXStrDiGraph

from sera.libs.directed_computing_graph._edge import DCGEdge
from sera.libs.directed_computing_graph._node import DCGNode, NodeId

TaskKey = Annotated[tuple, "TaskKey"]
TaskArgs = Annotated[MutableSequence, "TaskArgs"]


class ArgValueType(Enum):
    UNSET = "UNSET"
    SKIP = "SKIP"


UNSET = ArgValueType.UNSET
SKIP = ArgValueType.SKIP


@dataclass
class NodeRuntime:
    id: NodeId
    tasks: dict[TaskKey, TaskArgs]
    context: Sequence[Any]

    graph: RetworkXStrDiGraph[int, DCGNode, DCGEdge]
    node: DCGNode
    indegree: int
    # This is a mapping from parent node id to the index of the argument in the task.
    parent2argindex: dict[str, int]

    @staticmethod
    def from_node(
        graph: RetworkXStrDiGraph[int, DCGNode, DCGEdge],
        node: DCGNode,
        context: Sequence[Any],
    ) -> NodeRuntime:
        return NodeRuntime(
            id=node.id,
            tasks={},
            context=context,
            graph=graph,
            node=node,
            indegree=graph.in_degree(node.id),
            parent2argindex={
                edge.source: i
                # Map parent node ID to argument index based on sorted in-edge order
                for i, edge in enumerate(
                    sorted(graph.in_edges(node.id), key=lambda e: e.id)
                )
            },
        )

    def add_task(self, key: TaskKey, args: TaskArgs) -> NodeRuntime:
        """
        Add a task to the node runtime.

        Args:
            key: The key identifying the task.
            args: The arguments for the task.
        Returns:
            NodeRuntime: The updated node runtime with the new task added.
        """
        self.tasks[key] = args
        return self

    def add_task_args(
        self, key: TaskKey, parent_node: NodeId, argvalue: Any
    ) -> NodeRuntime:
        """
        Add an argument to an existing task.

        Args:
            key: The key identifying the task.
            parent_node: Identifier of the parent node from which the argument is coming.
            argvalue: The value of the argument to add.
        Returns:
            NodeRuntime: The updated node runtime with the new argument added to the task.
        """
        if key not in self.tasks:
            self.tasks[key] = [UNSET] * self.indegree
        self.tasks[key][self.parent2argindex[parent_node]] = argvalue
        return self

    def has_enough_data(self) -> bool:
        """
        Check if the node has enough data to execute its tasks.

        Returns:
            bool: True if the node has enough data, False otherwise.
        """
        return all(
            all(arg is not UNSET for arg in args) for args in self.tasks.values()
        )

    def execute(self, task: TaskArgs) -> Any:
        """
        Execute a task with the given context.

        Args:
            task (TaskArgs): The arguments for the task.
            context (dict): The context in which to execute the task.
        """
        norm_args = (self.node.type_conversions[i](a) for i, a in enumerate(task))
        return self.node.func(*norm_args, *self.context)
