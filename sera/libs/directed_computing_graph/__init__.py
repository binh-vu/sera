"""
Directed Computing Graph package for sera.

This package provides classes and utilities for working with directed computing graphs.
"""

# Import type aliases and annotated types
# Import all classes from submodules
from ._dcg import DirectedComputingGraph, NodeId, TaskArgs, TaskKey
from ._edge import DCGEdge
from ._flow import Flow
from ._node import ComputeFn, ComputeFnId, DCGNode, PartialFn
from ._runtime import SKIP, UNSET, ArgValueType, NodeRuntime

# Import utility functions from type conversion
from ._type_conversion import (
    ComposeTypeConversion,
    TypeConversion,
    UnitTypeConversion,
    align_generic_type,
    ground_generic_type,
    is_generic_type,
    patch_get_origin,
)

# Define __all__ to control what gets exported
__all__ = [
    # Main classes
    "DirectedComputingGraph",
    "DCGNode",
    "DCGEdge",
    "Flow",
    "PartialFn",
    "TypeConversion",
    "NodeRuntime",
    # Enums and special values
    "ArgValueType",
    "UNSET",
    "SKIP",
    # Type aliases and annotations
    "NodeId",
    "TaskKey",
    "TaskArgs",
    "ComputeFnId",
    "ComputeFn",
    "UnitTypeConversion",
    "ComposeTypeConversion",
    # Utility functions
    "patch_get_origin",
    "is_generic_type",
    "align_generic_type",
    "ground_generic_type",
]
