from __future__ import annotations

import re
from typing import Collection, Generic, cast

from litestar import Request, status_codes
from litestar.connection import ASGIConnection
from litestar.dto import MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.serialization import decode_json, decode_msgpack
from litestar.typing import FieldDefinition
from msgspec import Struct

from sera.libs.base_service import Query, QueryOp
from sera.libs.middlewares.uscp import STATE_SYSTEM_CONTROLLED_PROP_KEY
from sera.typing import T

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


class SingleAutoUSCP(MsgspecDTO[T], Generic[T]):
    """Auto Update System Controlled Property DTO"""

    @classmethod
    def create_for_field_definition(
        cls,
        field_definition: FieldDefinition,
        handler_id: str,
        backend_cls: type[DTOBackend] | None = None,
    ) -> None:
        assert backend_cls is None, "Custom backend not supported"
        super().create_for_field_definition(
            field_definition, handler_id, FixedDTOBackend
        )

    def decode_bytes(self, value: bytes):
        """Decode a byte string into an object"""
        backend = self._dto_backends[self.asgi_connection.route_handler.handler_id][
            "data_backend"
        ]  # pyright: ignore
        obj = backend.populate_data_from_raw(value, self.asgi_connection)
        obj.update_system_controlled_props(
            self.asgi_connection.scope["state"][STATE_SYSTEM_CONTROLLED_PROP_KEY]
        )
        return obj


class FixedDTOBackend(DTOCodegenBackend):
    def parse_raw(
        self, raw: bytes, asgi_connection: ASGIConnection
    ) -> Struct | Collection[Struct]:
        """Parse raw bytes into transfer model type.

        Note: instead of decoding into self.annotation, which I encounter this error: https://github.com/litestar-org/litestar/issues/4181; we have to use self.model_type, which is the original type.

        Args:
            raw: bytes
            asgi_connection: The current ASGI Connection

        Returns:
            The raw bytes parsed into transfer model type.
        """
        request_encoding = RequestEncodingType.JSON

        if (content_type := getattr(asgi_connection, "content_type", None)) and (
            media_type := content_type[0]
        ):
            request_encoding = media_type

        type_decoders = asgi_connection.route_handler.resolve_type_decoders()

        if request_encoding == RequestEncodingType.MESSAGEPACK:
            result = decode_msgpack(
                value=raw,
                target_type=self.model_type,
                type_decoders=type_decoders,
                strict=False,
            )
        else:
            result = decode_json(
                value=raw,
                target_type=self.model_type,
                type_decoders=type_decoders,
                strict=False,
            )

        return cast("Struct | Collection[Struct]", result)
