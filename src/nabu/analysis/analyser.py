from nabu.analysis.index import IRIndex
from nabu.backends.python.mapping import type_mapper
from nabu.config.loader import Config
from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result
from nabu.ir import operations
from nabu.ir.definitions import IRInterfaceType, IRObjectType, IRUnionType
from nabu.ir.document import IRDocument
from nabu.ir.location import SourceLocation
from nabu.ir.operations import (
    IRFieldSelection,
    IRFragmentSpread,
    IRInlineFragment,
    IROperationType,
    IRSelection,
)
from nabu.ir.types import (
    ListTypeRef,
    NamedTypeRef,
    NonNullTypeRef,
    TypeRef,
    unwrap_to_named,
)
from nabu.log import logger

_ROOT_MAP = {
    IROperationType.QUERY: "Query",
    IROperationType.MUTATION: "Mutation",
    IROperationType.SUBSCRIPTION: "Subscription",
}


def _to_pascal_case(name: str) -> str:
    return name[0].upper() + name[1:] if name else name


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
    logger.debug("Checking type references")
    diagnostics: list[Diagnostic] = []
    for obj in document.objects + document.inputs + document.interfaces:
        for field in obj.fields:
            _check_ref(field.type_ref, _location(field), index, diagnostics)
            for arg in field.arguments:
                _check_ref(arg.type_ref, _location(field), index, diagnostics)
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
    logger.debug("Checking custom scalars")
    return [
        _produce_error(
            ErrorCode.UNMAPPED_SCALAR,
            f"No Python mapping configured for custom scalar '{scalar.name}'.",
            _location(scalar),
            hint=f'Add to nabu.toml: [scalars]\n{scalar.name} = "..."',
        )
        for scalar in document.scalars
        if not scalar.builtin and scalar.name not in config.scalars
    ]


def _parent_type_after_field(
    field_name: str, parent: str, index: IRIndex
) -> str | None:
    field = index.field_of(parent, field_name)
    if field is None:
        return None
    named = unwrap_to_named(field.type_ref)
    return named.name if named else None


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

    for selection in selections:
        if isinstance(selection, IRFieldSelection):
            if is_union:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FIELD,
                        f"Cannot select field '{selection.name}' directly on union type '{parent_type}'. Use inline fragments.",
                        _location(selection),
                    )
                )
                continue

            next_type = _resolve_field(selection.name, parent_type, index)
            if next_type is None:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FIELD,
                        f"Field '{selection.name}' does not exist on type '{parent_type}'.",
                        _location(selection),
                    )
                )
                continue

            if selection.selections:
                _check_selection_set(
                    selection.selections, next_type, index, diagnostics
                )

        elif isinstance(selection, IRInlineFragment):
            if not index.is_defined(selection.on_type):
                diagnostics.append(
                    _produce_error(
                        ErrorCode.BAD_FRAGMENT_TARGET,
                        f"Inline fragment target type '{selection.on_type}' is not defined.",
                        None,
                    )
                )
            else:
                _check_selection_set(
                    selection.selections, selection.on_type, index, diagnostics
                )

        elif isinstance(selection, IRFragmentSpread):
            if selection.name not in index.fragments:
                diagnostics.append(
                    _produce_error(
                        ErrorCode.UNKNOWN_FRAGMENT,
                        f"Fragment '{selection.name}' is not defined.",
                        None,
                    )
                )


def _check_selections(document: IRDocument, index: IRIndex) -> list[Diagnostic]:
    logger.debug("Checking selections")
    diagnostics: list[Diagnostic] = []
    for operation in document.operations:
        logger.debug("Checking selections for operation %s", operation.name)
        _check_selection_set(
            operation.selections,
            _ROOT_MAP[operation.operation_type],
            index,
            diagnostics,
        )
    return diagnostics


def _check_fragments(document: IRDocument, index: IRIndex) -> list[Diagnostic]:
    logger.debug("Checking fragments")
    diagnostics: list[Diagnostic] = []
    for fragment in document.fragments:
        if not index.is_defined(fragment.on_type):
            diagnostics.append(
                _produce_error(
                    ErrorCode.BAD_FRAGMENT_TARGET,
                    f"Fragment '{fragment.name}' targets undefined type '{fragment.on_type}'.",
                    None,
                )
            )
        else:
            _check_selection_set(
                fragment.selections, fragment.on_type, index, diagnostics
            )
    return diagnostics


def _check_naming(document: IRDocument) -> list[Diagnostic]:
    logger.debug("Checking naming")
    diagnostics: list[Diagnostic] = []
    seen: dict[str, str] = {}

    for type_ in (
        document.objects
        + document.inputs
        + document.enums
        + document.interfaces
        + document.unions
    ):
        cls = _to_pascal_case(type_.name)
        if cls in seen:
            diagnostics.append(
                _produce_error(
                    ErrorCode.NAME_COLLISION,
                    f"Types '{type_.name}' and '{seen[cls]}' both produce the identifier '{cls}'.",
                    None,
                )
            )
        else:
            seen[cls] = type_.name

    return diagnostics


def _check_unsupported(document: IRDocument) -> list[Diagnostic]:
    logger.debug("Checking unsupported features")
    return [
        _produce_error(
            ErrorCode.UNSUPPORTED_FEATURE,
            f"Subscription operation '{operation.name}' is not supported by Nabu Forge.",
            _location(operation),
            hint="Remove the subscription or implement it separately.",
        )
        for operation in document.operations
        if operation.operation_type == IROperationType.SUBSCRIPTION
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
