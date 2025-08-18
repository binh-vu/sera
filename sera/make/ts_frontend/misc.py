from __future__ import annotations

from typing import Optional

from codegen.models import AST, ImportHelper, PredefinedFn, Program, expr, stmt

from sera.models import (
    Class,
    DataProperty,
    Enum,
    ObjectProperty,
    Package,
    Schema,
    TsTypeWithDep,
)

TS_GLOBAL_IDENTS = {
    "normalizers.normalizeNumber": "sera-db.normalizers",
    "normalizers.normalizeOptionalNumber": "sera-db.normalizers",
    "normalizers.normalizeDate": "sera-db.normalizers",
    "normalizers.normalizeOptionalDate": "sera-db.normalizers",
}


def get_normalizer(
    tstype: TsTypeWithDep, import_helper: ImportHelper
) -> Optional[expr.ExprIdent]:
    if tstype.type == "number":
        return import_helper.use("normalizers.normalizeNumber")
    if tstype.type == "number | undefined":
        return import_helper.use("normalizers.normalizeOptionalNumber")
    if tstype.type == "Date":
        return import_helper.use("normalizers.normalizeDate")
    if tstype.type == "Date | undefined":
        return import_helper.use("normalizers.normalizeOptionalDate")

    assert "number" not in tstype.type, tstype.type
    return None
