import keyword
import re
import typing

from graphql import OperationType

from nabu.analysis.index import IRIndex
from nabu.config.loader import Config
from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result
from nabu.ir.definitions import IRObjectType, IRUnionType
from nabu.ir.document import IRDocument
from nabu.ir.location import SourceLocation
from nabu.ir.operations import (
    IRFieldSelection,
    IRFragmentSpread,
    IRInlineFragment,
    IRSelection,
)
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef, TypeRef

_ROOT_MAP = {
    OperationType.QUERY: "Query",
    OperationType.MUTATION: "Mutation",
    OperationType.SUBSCRIPTION: "Subscription",
}


def _location(node) -> SourceLocation | None:
    return getattr(node, "source_location", None)


def _produce_error(
    code: ErrorCode,
    message: str,
    loc: SourceLocation | None,
    hint: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        file=loc.file if loc else None,
        line=loc.line if loc else None,
        column=loc.column if loc else None,
        hint=hint,
    )


def _named_refs(type_ref: TypeRef) -> list[str]:
    if isinstance(type_ref, NamedTypeRef):
        return [type_ref.name]
    if isinstance(type_ref, NonNullTypeRef):
        return _named_refs(type_ref.inner)
    if isinstance(type_ref, ListTypeRef):
        return _named_refs(type_ref.item)
    return []


def _to_class_name(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _to_field_name(name: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")


def _check_ref(
    type_ref: TypeRef,
    loc: SourceLocation | None,
    index: IRIndex,
    diagnostics: list[Diagnostic],
) -> None:
    for name in _named_refs(type_ref):
        if not index.is_defined(name):
            diagnostics.append(
                _produce_error(
                    ErrorCode.UNKNOWN_TYPE_REF,
                    f"Unknown type '{name}' referenced in the schema.",
                    loc,
                    hint="Define the type in the schema or add a scalar mapping in nabu.toml.",
                )
            )


def _check_type_references(document: IRDocument, index: IRIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for obj in document.objects + document.inputs + document.interfaces:
        for f in obj.fields:
            _check_ref(f.type_ref, _location(f), index, diagnostics)
            for arg in f.arguments:
                _check_ref(arg.type_ref, _location(f), index, diagnostics)
    for op in document.operations:
        for var in op.variables:
            if not index.is_defined(next(iter(_named_refs(var.type_ref)), "")):
                for name in _named_refs(var.type_ref):
                    diagnostics.append(
                        _produce_error(
                            ErrorCode.UNKNOWN_VARIABLE_TYPE,
                            f"Variable '${var.name}' references unknown type '{name}'.",
                            _location(op),
                        )
                    )
    return diagnostics


def _check_custom_scalars(document: IRDocument, config: Config) -> list[Diagnostic]:
    return [
        _produce_error(
            ErrorCode.UNMAPPED_SCALAR,
            f"No Python mapping configured for custom scalar '{s.name}'.",
            _location(s),
            hint=f'Add to nabu.toml: [scalars]\n{s.name} = "..."',
        )
        for s in document.scalars
        if not s.builtin and s.name not in config.scalars
    ]


def _parent_type_after_field(
    field_name: str, parent: str, index: IRIndex
) -> str | None:
    f = index.field_of(parent, field_name)
    if f is None:
        return None
    ref = f.type_ref
    while isinstance(ref, (NonNullTypeRef, ListTypeRef)):
        ref = ref.inner if isinstance(ref, NonNullTypeRef) else ref.item
    return ref.name if isinstance(ref, NamedTypeRef) else None


def _resolve_field(selection_name: str, parent_type: str, index: IRIndex) -> str | None:
    next_type = _parent_type_after_field(selection_name, parent_type, index)
    if next_type is not None:
        return next_type
    obj = index.types.get(parent_type)
    if isinstance(obj, IRObjectType):
        for iface in obj.interfaces:
            candidate = _parent_type_after_field(selection_name, iface, index)
            if candidate is not None:
                return candidate
    return None


def _check_selection_set(
    selections: list[IRSelection],
    parent_type: str,
    index: IRIndex,
    diagnostics: list[Diagnostic],
) -> None:
    is_union = isinstance(index.types.get(parent_type), IRUnionType)

    for sel in selections:
        if isinstance(sel, IRFieldSelection):
            if is_union:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FIELD,
                        f"Cannot select field '{sel.name}' directly on union type '{parent_type}'. Use inline fragments.",
                        _location(sel),
                    )
                )
                continue

            next_type = _resolve_field(sel.name, parent_type, index)
            if next_type is None:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FIELD,
                        f"Field '{sel.name}' does not exist on type '{parent_type}'.",
                        _location(sel),
                    )
                )
                continue

            if sel.selections:
                _check_selection_set(sel.selections, next_type, index, diagnostics)

        elif isinstance(sel, IRInlineFragment):
            if not index.is_defined(sel.on_type):
                diagnostics.append(
                    _produce_error(
                        ErrorCode.BAD_FRAGMENT_TARGET,
                        f"Inline fragment target type '{sel.on_type}' is not defined.",
                        None,
                    )
                )
            else:
                _check_selection_set(sel.selections, sel.on_type, index, diagnostics)

        elif isinstance(sel, IRFragmentSpread):
            if sel.name not in index.fragments:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FRAGMENT,
                        f"Fragment '{sel.name}' is not defined.",
                        None,
                    )
                )


def _check_selections(document: IRDocument, index: IRIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for op in document.operations:
        _check_selection_set(
            op.selections, _ROOT_MAP[op.operation_type], index, diagnostics
        )
    return diagnostics


def _check_fragments(document: IRDocument, index: IRIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for frag in document.fragments:
        if not index.is_defined(frag.on_type):
            diagnostics.append(
                _produce_error(
                    ErrorCode.BAD_FRAGMENT_TARGET,
                    f"Fragment '{frag.name}' targets undefined type '{frag.on_type}'.",
                    None,
                )
            )
        else:
            _check_selection_set(frag.selections, frag.on_type, index, diagnostics)
    return diagnostics


def _check_naming(document: IRDocument) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    seen: dict[str, str] = {}

    for t in (
        document.objects
        + document.inputs
        + document.enums
        + document.interfaces
        + document.unions
    ):
        cls = _to_class_name(t.name)
        if cls in seen:
            diagnostics.append(
                _produce_error(
                    ErrorCode.NAME_COLLISION,
                    f"Types '{t.name}' and '{seen[cls]}' both generate Python class name '{cls}'.",
                    None,
                )
            )
        else:
            seen[cls] = t.name

        if hasattr(t, "fields"):
            for f in t.fields:
                py = _to_field_name(f.name)
                if keyword.iskeyword(py):
                    diagnostics.append(
                        _produce_error(
                            ErrorCode.RESERVED_NAME,
                            f"Field '{f.name}' maps to Python keyword '{py}' in type '{t.name}'.",
                            _location(f),
                        )
                    )

    return diagnostics


def _check_unsupported(document: IRDocument) -> list[Diagnostic]:
    return [
        _produce_error(
            ErrorCode.UNSUPPORTED_FEATURE,
            f"Subscription operation '{op.name}' is not supported by Nabu Forge.",
            _location(op),
            hint="Remove the subscription or implement it separately.",
        )
        for op in document.operations
        if op.operation_type == OperationType.SUBSCRIPTION
    ]

def analyse(document: IRDocument, config: Config) -> Result[IRDocument]:
    index = IRIndex(document)
    diagnostics: list[Diagnostic] = (
        _check_type_references(document, index)
        + _check_custom_scalars(document, config)
        + _check_selections(document, index)
        + _check_fragments(document, index)
        + _check_naming(document)
        + _check_unsupported(document)
    )
    return Result(value=document, diagnostics=diagnostics)
