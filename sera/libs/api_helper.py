from __future__ import annotations

import re

from litestar import Request, status_codes
from litestar.exceptions import HTTPException
from sera.libs.base_service import Query, QueryOp

# for parsing field names and operations from query string
FIELD_REG = re.compile(r"(?P<name>[a-zA-Z_0-9]+)(?:\[(?P<op>[a-zA-Z0-9]+)\])?")
QUERY_OPS = {op.value for op in QueryOp}
KEYWORDS = {"field", "limit", "offset", "unique", "sorted_by", "group_by"}


def parse_query(request: Request, fields: set[str], debug: bool) -> Query:
    """Parse query for retrieving records that match a query.

    If a field name collides with a keyword, you can add `_` to the field name.

    To filter records, you can apply a condition on a column using <field>=<value> (equal condition). Or you can
    be explicit by using <field>[op]=<value>, where op is one of the operators defined in QueryOp.
    """
    query: Query = {}

    for k, v in request.query_params.items():
        if k in KEYWORDS:
            continue
        m = FIELD_REG.match(k)
        if m:
            field_name = m.group("name")
            operation = m.group("op")  # This will be None if no operation is specified

            # If field name ends with '_' and it's to avoid keyword conflict, remove it
            if field_name.endswith("_") and field_name[:-1] in KEYWORDS:
                field_name = field_name[:-1]

            if field_name not in fields:
                # Invalid field name, skip
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid field name: {field_name}",
                    )
                continue

            # Process based on operation or default to equality check
            if not operation:
                operation = QueryOp.eq
            else:
                if operation not in QUERY_OPS:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid operation: {operation}",
                    )
                operation = QueryOp(operation)
            query[field_name] = {operation: v}
        else:
            # Invalid field name format
            if debug:
                raise HTTPException(
                    status_code=status_codes.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid field name: {k}",
                )
            continue

    return query
