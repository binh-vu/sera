from __future__ import annotations

from typing import Collection, Generic, TypeVar, cast

from litestar.connection import ASGIConnection
from litestar.dto import MsgspecDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.enums import RequestEncodingType
from litestar.serialization import decode_json, decode_msgpack
from litestar.typing import FieldDefinition
from msgspec import Struct

from sera.libs.middlewares.uscp import SKIP_UPDATE_SYSTEM_CONTROLLED_PROPS_KEY

S = TypeVar("S", bound=Struct)


class SingleAutoUSCP(MsgspecDTO[S], Generic[S]):
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
        if self.asgi_connection.scope["state"][SKIP_UPDATE_SYSTEM_CONTROLLED_PROPS_KEY]:
            # Skip updating system-controlled properties
            # TODO: dirty fix as this assumes every struct has _is_scp_updated property. find a
            # better solution and fix me!
            obj._is_scp_updated = True
            return obj

        obj.update_system_controlled_props(self.asgi_connection)
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
