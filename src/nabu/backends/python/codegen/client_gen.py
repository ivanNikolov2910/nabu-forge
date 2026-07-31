import re
from pathlib import Path

from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.ir.operations import IROperation, IRVariable
from nabu.ir.types import NonNullTypeRef, unwrap_to_named

_OPERATION_START = re.compile(r"\b(query|mutation|subscription)\s+(\w+)")
_FRAGMENT_SPREAD = re.compile(r"\.\.\.\s*(\w+)")
_FRAGMENT_DEF = re.compile(r"\bfragment\s+(\w+)\b")


def _extract_block(text: str, start: int) -> str:
    """Return the definition starting at `start`, up to its matching brace."""
    brace_open = text.index("{", start)
    depth = 0
    for i in range(brace_open, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _operation_documents(op_files: list[Path]) -> dict[str, str]:
    """Map each operation name -> a self-contained document string.

    Extracts only that operation's definition (not the whole file, which may
    hold several operations) plus any named fragments it spreads, so the server
    receives exactly one operation."""
    documents: dict[str, str] = {}
    for path in op_files:
        text = path.read_text(encoding="utf-8")
        # index every fragment definition in this file by name
        fragments = {
            m.group(1): _extract_block(text, m.start())
            for m in _FRAGMENT_DEF.finditer(text)
        }
        for match in _OPERATION_START.finditer(text):
            op_name = match.group(2)
            block = _extract_block(text, match.start())
            # append any fragments this operation (transitively) spreads
            needed: list[str] = []
            seen: set[str] = set()
            pending = _FRAGMENT_SPREAD.findall(block)
            while pending:
                frag = pending.pop()
                if frag in seen or frag not in fragments:
                    continue
                seen.add(frag)
                needed.append(fragments[frag])
                pending.extend(_FRAGMENT_SPREAD.findall(fragments[frag]))
            documents[op_name] = "\n\n".join([block, *needed])
    return documents


def _method_params(variables: list[IRVariable], scalars: dict[str, str]) -> str:
    """Build the method signature fragment, required params before optional."""
    required, optional = [], []
    for var in variables:
        annotation = map_type(var.type_ref, scalars)
        name = to_field_name(var.name)
        if isinstance(var.type_ref, NonNullTypeRef):
            required.append(f"{name}: {annotation}")
        else:
            optional.append(f"{name}: {annotation} = None")
    parts = required + optional
    return (", " + ", ".join(parts)) if parts else ""


def _document_const(operation: IROperation) -> str:
    return to_field_name(operation.name).upper() + "_DOCUMENT"


def generate_client(document: IRDocument, op_files: list[Path], config: Config) -> str:
    scalars = scalar_table(config.scalars)
    documents = _operation_documents(op_files)
    input_names = {i.name for i in document.inputs}

    operations = []
    result_imports = []
    used_inputs: set[str] = set()
    for operation in document.operations:
        module = to_field_name(operation.name)
        result_class = f"{to_class_name(operation.name)}Result"
        result_imports.append({"module": module, "result_class": result_class})

        for var in operation.variables:
            named = unwrap_to_named(var.type_ref)
            if named and named.name in input_names:
                used_inputs.add(named.name)

        operations.append(
            {
                "method_name": module,
                "document_const": _document_const(operation),
                "document_text": documents.get(operation.name, "").strip(),
                "result_class": result_class,
                "params": _method_params(operation.variables, scalars),
                "variables": [
                    {"gql_name": v.name, "py_name": to_field_name(v.name)}
                    for v in operation.variables
                ],
            }
        )

    input_imports = sorted(to_class_name(name) for name in used_inputs)

    return render(
        "client.py.jinja",
        {
            "operations": operations,
            "result_imports": result_imports,
            "input_imports": input_imports,
        },
    )
