from __future__ import annotations

from typing import Dict, List, Optional, Union, cast

import pytest

from sera.libs.directed_computing_graph import (
    SKIP,
    UNSET,
    ComposeTypeConversion,
    ComputeFn,
    ComputeFnId,
    DCGEdge,
    DCGNode,
    DirectedComputingGraph,
    Flow,
    NodeRuntime,
    PartialFn,
    TypeConversion,
    UnitTypeConversion,
)


class TestDirectedComputingGraph:
    """Test suite for DirectedComputingGraph functionality."""

    def test_simple_computation(self):
        """Test basic computation with simple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        def multiply(x: int, factor: int) -> int:
            return x * factor

        # Input functions that just return their input
        def input1_fn(x: int) -> int:
            return x

        def input2_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input1": input1_fn,
            "input2": input2_fn,
            "add": Flow(["input1", "input2"], add),
            "multiply": Flow(["add"], multiply),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(
            input={"input1": (5,), "input2": (3,)},
            output={"multiply"},
            context={"factor": 2},
        )

        assert result["multiply"] == [16]  # (5 + 3) * 2 = 16

    def test_multiple_inputs_outputs(self):
        """Test graph with multiple inputs and outputs."""

        def square(x: int) -> int:
            return x * x

        def cube(x: int) -> int:
            return x * x * x

        def add(x: int, y: int) -> int:
            return x + y

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "square": Flow(["input"], square),
            "cube": Flow(["input"], cube),
            "sum": Flow(["square", "cube"], add),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(input={"input": (3,)}, output={"square", "cube", "sum"})

        assert result["square"] == [9]  # 3^2 = 9
        assert result["cube"] == [27]  # 3^3 = 27
        assert result["sum"] == [36]  # 9 + 27 = 36

    def test_partial_functions(self):
        """Test using PartialFn with default arguments."""

        def multiply(x: int, factor: int = 2) -> int:
            return x * factor

        def power(x: int, exponent: int = 2) -> int:
            return x**exponent

        def input_fn(x: int) -> int:
            return x

        # Create partial function with different default
        partial_multiply = PartialFn(multiply, factor=3)

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "multiply": Flow(["input"], partial_multiply),
            "power": Flow(["multiply"], power),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(
            input={"input": (4,)}, output={"multiply", "power"}, context={"exponent": 3}
        )

        assert result["multiply"] == [12]  # 4 * 3 = 12
        assert result["power"] == [1728]  # 12^3 = 1728

    def test_context_arguments(self):
        """Test functions that require context arguments."""

        def add_with_offset(x: int, offset: int) -> int:
            return x + offset

        def scale(x: int, scale_factor: float) -> float:
            return x * scale_factor

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "add_offset": Flow(["input"], add_with_offset),
            "scale": Flow(["add_offset"], scale),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(
            input={"input": (10,)},
            output={"add_offset", "scale"},
            context={"offset": 5, "scale_factor": 1.5},
        )

        assert result["add_offset"] == [15]  # 10 + 5 = 15
        assert result["scale"] == [22.5]  # 15 * 1.5 = 22.5

    def test_callable_context(self):
        """Test using callable context function."""

        def add_random(x: int, random_value: int) -> int:
            return x + random_value

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "add_random": Flow(["input"], add_random),
        }

        def get_context():
            return {"random_value": 42}

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(
            input={"input": (8,)}, output={"add_random"}, context=get_context
        )

        assert result["add_random"] == [50]  # 8 + 42 = 50

    def test_skip_functionality(self):
        """Test SKIP functionality with filter functions."""

        def positive_only(x: int) -> int:
            return x

        def double(x: int) -> int:
            return x * 2

        def is_positive(value: int) -> bool:
            return value > 0

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "positive": Flow(["input"], positive_only),
            "double": Flow(["positive"], double, filter_fn=is_positive),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        # Test with positive number
        result_pos = dcg.execute(input={"input": (5,)}, output={"double"})
        assert result_pos["double"] == [10]

        # Test with negative number (should be skipped)
        result_neg = dcg.execute(input={"input": (-3,)}, output={"double"})
        assert result_neg["double"] == [SKIP]

    def test_type_conversion(self):
        """Test type conversion functionality."""

        def int_to_str(x: int) -> str:
            return str(x)

        def str_to_float(x: str) -> float:
            return float(x)

        def add_numbers(x: float, y: float) -> float:
            return x + y

        def identity(x: int) -> int:
            return x

        def input_fn(x: int) -> int:
            return x

        def input2_fn(x: float) -> float:
            return x

        # Define type conversion functions
        type_conversions = [int_to_str, str_to_float]

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "input2": input2_fn,
            "convert": Flow(["input"], identity),  # identity function
            "add": Flow(["convert", "input2"], add_numbers),
        }

        dcg = DirectedComputingGraph.from_flows(flows, type_conversions, strict=False)

        result = dcg.execute(input={"input": (42,), "input2": (3.14,)}, output={"add"})

        # Should convert 42 to "42" to 42.0, then add 42.0 + 3.14
        assert abs(result["add"][0] - 45.14) < 0.001

    def test_complex_dependency_graph(self):
        """Test a complex graph with multiple dependencies."""

        def add(x: int, y: int) -> int:
            return x + y

        def subtract(x: int, y: int) -> int:
            return x - y

        def multiply(x: int, y: int) -> int:
            return x * y

        def divide(x: int, y: int) -> float:
            return x / y if y != 0 else 0.0

        def a_fn(x: int) -> int:
            return x

        def b_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "a": a_fn,
            "b": b_fn,
            "sum": Flow(["a", "b"], add),
            "diff": Flow(["a", "b"], subtract),
            "product": Flow(["sum", "diff"], multiply),
            "quotient": Flow(["sum", "diff"], divide),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(
            input={"a": (10,), "b": (4,)}, output={"sum", "diff", "product", "quotient"}
        )

        assert result["sum"] == [14]  # 10 + 4 = 14
        assert result["diff"] == [6]  # 10 - 4 = 6
        assert result["product"] == [84]  # 14 * 6 = 84
        assert result["quotient"] == [14 / 6]  # 14 / 6 ≈ 2.33

    def test_node_runtime(self):
        """Test NodeRuntime functionality."""
        from graph.retworkx import RetworkXStrDiGraph

        def add(x: int, y: int) -> int:
            return x + y

        # Create a simple graph
        graph = RetworkXStrDiGraph(check_cycle=False, multigraph=False)
        node = DCGNode("add", add)
        graph.add_node(node)

        # Initialize the node's type conversions properly
        node.type_conversions = [lambda x: x, lambda x: x]  # identity conversions

        runtime = NodeRuntime.from_node(graph, node)

        # Test adding tasks
        runtime.add_task((0,), [1, 2])
        assert (0,) in runtime.tasks
        assert runtime.tasks[(0,)] == [1, 2]

        # Test has_enough_data when complete
        assert runtime.has_enough_data()

        # Test execution
        result = runtime.execute([3, 4], {})
        assert result == 7

    def test_edge_filter(self):
        """Test DCGEdge filter functionality."""
        from sera.misc import identity

        def is_even(x: int) -> bool:
            return x % 2 == 0

        edge = DCGEdge(
            id=1,
            source="source",
            target="target",
            argindex=0,
            type_conversion=identity,
            filter_fn=is_even,
        )

        assert edge.filter(4) == True  # 4 is even
        assert edge.filter(3) == False  # 3 is odd

        # Test edge without filter
        edge_no_filter = DCGEdge(
            id=2, source="source", target="target", argindex=0, type_conversion=identity
        )

        assert edge_no_filter.filter(42) == True  # Always true when no filter

    def test_flow_creation(self):
        """Test Flow creation with different source types."""

        def dummy_func(x: int) -> int:
            return x

        # Test with single source
        flow1 = Flow("input1", dummy_func)
        assert flow1.source == ["input1"]

        # Test with multiple sources
        flow2 = Flow(["input1", "input2"], dummy_func)
        assert flow2.source == ["input1", "input2"]

        # Test with filter function
        def filter_positive(x: int) -> bool:
            return x > 0

        flow3 = Flow("input", dummy_func, filter_fn=filter_positive)
        assert flow3.filter_fn == filter_positive

    def test_empty_graph(self):
        """Test behavior with empty flows."""
        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {}
        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(input={}, output=set())
        assert result == {}

    def test_no_context_functions(self):
        """Test functions that don't require context."""

        def identity(x: int) -> int:
            return x

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "identity": Flow(["input"], identity),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        result = dcg.execute(input={"input": (42,)}, output={"identity"})

        assert result["identity"] == [42]

    def test_error_handling(self):
        """Test error handling in various scenarios."""

        def failing_function(x: int) -> int:
            if x < 0:
                raise ValueError("Negative input not allowed")
            return x * 2

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "process": Flow(["input"], failing_function),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        # Test with valid input
        result = dcg.execute(input={"input": (5,)}, output={"process"})
        assert result["process"] == [10]

        # Test with invalid input should raise exception
        with pytest.raises(ValueError, match="Negative input not allowed"):
            dcg.execute(input={"input": (-1,)}, output={"process"})

    def test_partial_fn_invalid_args(self):
        """Test PartialFn with invalid argument names."""

        def add(x: int, y: int) -> int:
            return x + y

        # Test with invalid argument name
        with pytest.raises(
            Exception, match="Argument z is not in the function signature"
        ):
            PartialFn(add, z=5)

    def test_multiple_tasks(self):
        """Test graph with multiple independent task executions."""

        def square(x: int) -> int:
            return x * x

        def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "square": Flow(["input"], square),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        # Execute multiple times with different inputs
        result1 = dcg.execute(input={"input": (3,)}, output={"square"})

        result2 = dcg.execute(input={"input": (4,)}, output={"square"})

        assert result1["square"] == [9]
        assert result2["square"] == [16]
