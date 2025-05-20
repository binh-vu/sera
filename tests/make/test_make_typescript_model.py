"""Tests for the TypeScript model generation module."""

import pytest

from sera.make.make_typescript_model import _inject_type_for_invalid_value
from sera.models import TsTypeWithDep


class TestInjectTypeForInvalidValue:
    """Tests for the _inject_type_for_invalid_value function."""

    def test_array_types(self):
        """Test handling of array types."""
        # Test case 1: Array type without string in inner type
        input_type = TsTypeWithDep("number[]", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | string)[]"
        assert result.dep is None

        # Test case 2: Array type with parenthesized union type
        input_type = TsTypeWithDep("(number | undefined)[]", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | undefined | string)[]"
        assert result.dep is None

        # Test case 3: Array type with string already included
        input_type = TsTypeWithDep("(number | string)[]", "some-dep")
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | string)[]"
        assert result.dep == "some-dep"

    def test_scalar_types(self):
        """Test handling of scalar types."""
        # Test case 1: Simple type
        input_type = TsTypeWithDep("number", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | string)"
        assert result.dep is None

        # Test case 2: Union type
        input_type = TsTypeWithDep("number | undefined", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | undefined | string)"
        assert result.dep is None

        # Test case 3: Type already contains string
        input_type = TsTypeWithDep("string", "some-dep")
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "string"
        assert result.dep == "some-dep"

        # Test case 4: Union type with string already included
        input_type = TsTypeWithDep("(number | string | undefined)", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | string | undefined)"
        assert result.dep is None

    def test_already_parenthesized_types(self):
        """Test handling of already parenthesized types."""
        # Test case 1: Already parenthesized simple type
        input_type = TsTypeWithDep("(number)", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | string)"
        assert result.dep is None

        # Test case 2: Already parenthesized union type
        input_type = TsTypeWithDep("(number | undefined)", "some-dep")
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | undefined | string)"
        assert result.dep == "some-dep"

    def test_unsupported_types(self):
        """Test handling of unsupported types."""
        # Test case: Complex type that doesn't match the expected patterns
        with pytest.raises(NotImplementedError):
            _inject_type_for_invalid_value(
                TsTypeWithDep("Record<string, number>", None)
            )

    def test_edge_cases(self):
        """Test handling of edge cases."""
        # Test case 1: Mixed alphanumeric type names
        input_type = TsTypeWithDep("MyCustomType", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(MyCustomType | string)"
        assert result.dep is None

        # Test case 2: Type with spaces
        input_type = TsTypeWithDep("number | null | undefined", None)
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | null | undefined | string)"
        assert result.dep is None

        # Test case 3: Array with complex inner type
        input_type = TsTypeWithDep("(number | null | undefined)[]", "some-dep")
        result = _inject_type_for_invalid_value(input_type)
        assert result.type == "(number | null | undefined | string)[]"
        assert result.dep == "some-dep"
