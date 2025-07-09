from __future__ import annotations

from typing import Dict, Union

import pytest

from sera.libs.directed_computing_graph import (
    ComputeFn,
    ComputeFnId,
    DirectedComputingGraph,
    Flow,
    PartialFn,
)


class TestDirectedComputingGraphAsyncExecution:
    """Test suite for DirectedComputingGraph async execution."""

    @pytest.mark.asyncio
    async def test_simple_computation(self):
        """Test basic computation with simple functions."""

        async def add(x: int, y: int) -> int:
            return x + y

        async def multiply(x: int, factor: int) -> int:
            return x * factor

        # Input functions that just return their input
        async def input1_fn(x: int) -> int:
            return x

        async def input2_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input1": input1_fn,
            "input2": input2_fn,
            "add": Flow(["input1", "input2"], add),
            "multiply": Flow(["add"], multiply),
        }

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input1": (5,), "input2": (3,)},
            output={"multiply"},
            context={"factor": 2},
        )

        assert result["multiply"] == [16]  # (5 + 3) * 2 = 16

    @pytest.mark.asyncio
    async def test_multiple_inputs_outputs(self):
        """Test graph with multiple inputs and outputs."""

        async def square(x: int) -> int:
            return x * x

        async def cube(x: int) -> int:
            return x * x * x

        async def add(x: int, y: int) -> int:
            return x + y

        async def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "square": Flow(["input"], square),
            "cube": Flow(["input"], cube),
            "sum": Flow(["square", "cube"], add),
        }

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input": (3,)}, output={"square", "cube", "sum"}
        )

        assert result["square"] == [9]  # 3^2 = 9
        assert result["cube"] == [27]  # 3^3 = 27
        assert result["sum"] == [36]  # 9 + 27 = 36

    @pytest.mark.asyncio
    async def test_partial_functions(self):
        """Test using PartialFn with default arguments."""

        async def multiply(x: int, factor: int = 2) -> int:
            return x * factor

        async def power(x: int, exponent: int = 2) -> int:
            return x**exponent

        async def input_fn(x: int) -> int:
            return x

        # Create partial function with different default
        partial_multiply = PartialFn(multiply, factor=3)

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "multiply": Flow(["input"], partial_multiply),
            "power": Flow(["multiply"], power),
        }

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input": (4,)}, output={"multiply", "power"}, context={"exponent": 3}
        )

        assert result["multiply"] == [12]  # 4 * 3 = 12
        assert result["power"] == [1728]  # 12^3 = 1728

    @pytest.mark.asyncio
    async def test_context_arguments(self):
        """Test functions that require context arguments."""

        async def add_with_offset(x: int, offset: int) -> int:
            return x + offset

        async def scale(x: int, scale_factor: float) -> float:
            return x * scale_factor

        async def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "add_offset": Flow(["input"], add_with_offset),
            "scale": Flow(["add_offset"], scale),
        }

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input": (10,)},
            output={"add_offset", "scale"},
            context={"offset": 5, "scale_factor": 1.5},
        )

        assert result["add_offset"] == [15]  # 10 + 5 = 15
        assert result["scale"] == [22.5]  # 15 * 1.5 = 22.5

    @pytest.mark.asyncio
    async def test_callable_context(self):
        """Test using callable context function."""

        async def add_random(x: int, random_value: int) -> int:
            return x + random_value

        async def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "add_random": Flow(["input"], add_random),
        }

        def get_context():
            return {"random_value": 42}

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input": (8,)}, output={"add_random"}, context=get_context
        )

        assert result["add_random"] == [50]  # 8 + 42 = 50

    @pytest.mark.asyncio
    async def test_edge_filter(self):
        """Test SKIP functionality with filter functions."""

        async def positive_only(x: int) -> int:
            return x

        async def double(x: int) -> int:
            return x * 2

        def is_positive(value: int) -> bool:
            return value > 0

        async def input_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "positive": Flow(["input"], positive_only),
            "double": Flow(["positive"], double, filter_fn=is_positive),
        }

        dcg = DirectedComputingGraph.from_flows(flows, strict=False)

        # Test with positive number
        result_pos = await dcg.execute_async(input={"input": (5,)}, output={"double"})
        assert result_pos["double"] == [10]

        # Test with negative number (should be skipped)
        result_neg = await dcg.execute_async(input={"input": (-3,)}, output={"double"})
        assert result_neg["double"] == []

    @pytest.mark.asyncio
    async def test_type_conversion(self):
        """Test type conversion functionality."""

        async def int_to_str(x: int) -> str:
            return str(x)

        def str_to_float(x: str) -> float:
            return float(x)

        async def add_numbers(x: float, y: float) -> float:
            return x + y

        async def input_fn(x: int) -> int:
            return x

        async def input2_fn(x: float) -> float:
            return x

        # Define type conversion functions
        type_conversions = [str_to_float]

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input": input_fn,
            "input2": input2_fn,
            "convert": Flow(["input"], int_to_str),  # convert int to str
            "add": Flow(["convert", "input2"], add_numbers),
        }

        dcg = DirectedComputingGraph.from_flows(flows, type_conversions)

        result = await dcg.execute_async(
            input={"input": (42,), "input2": (3.14,)}, output={"add"}
        )

        # Should convert 42 to "42" to 42.0, then add 42.0 + 3.14
        assert abs(result["add"][0] - 45.14) < 0.001

    @pytest.mark.asyncio
    async def test_complex_dependency_graph(self):
        """Test a complex graph with multiple dependencies."""

        async def add(x: int, y: int) -> int:
            return x + y

        async def subtract(x: int, y: int) -> int:
            return x - y

        async def multiply(x: int, y: int) -> int:
            return x * y

        async def divide(x: int, y: int) -> float:
            return x / y if y != 0 else 0.0

        async def a_fn(x: int) -> int:
            return x

        async def b_fn(x: int) -> int:
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

        result = await dcg.execute_async(
            input={"a": (10,), "b": (4,)}, output={"sum", "diff", "product", "quotient"}
        )

        assert result["sum"] == [14]  # 10 + 4 = 14
        assert result["diff"] == [6]  # 10 - 4 = 6
        assert result["product"] == [84]  # 14 * 6 = 84
        assert result["quotient"] == [14 / 6]  # 14 / 6 ≈ 2.33

    @pytest.mark.asyncio
    async def test_mixed_async_sync_function(self):
        """Test basic computation with simple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        async def multiply(x: int, factor: int) -> int:
            return x * factor

        # Input functions that just return their input
        async def input1_fn(x: int) -> int:
            return x

        async def input2_fn(x: int) -> int:
            return x

        flows: Dict[ComputeFnId, Union[Flow, ComputeFn]] = {
            "input1": input1_fn,
            "input2": input2_fn,
            "add": Flow(["input1", "input2"], add),
            "multiply": Flow(["add"], multiply),
        }

        dcg = DirectedComputingGraph.from_flows(flows)

        result = await dcg.execute_async(
            input={"input1": (5,), "input2": (3,)},
            output={"multiply"},
            context={"factor": 2},
        )

        assert result["multiply"] == [16]  # (5 + 3) * 2 = 16
