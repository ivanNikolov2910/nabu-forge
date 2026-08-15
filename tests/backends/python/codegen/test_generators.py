import importlib
import sys
from pathlib import Path

import pytest
from graphql import Source, build_schema, parse

from nabu.backends.python.codegen.enum_gen import generate_enums
from nabu.backends.python.codegen.exports_gen import generate_exports
from nabu.backends.python.codegen.input_gen import generate_inputs
from nabu.backends.python.codegen.model_gen import generate_models
from nabu.backends.python.codegen.operation_gen import (
    generate_operation,
    generate_operations,
)
from nabu.backends.python.codegen.ordering import dependency_order
from nabu.backends.python.codegen.scalars_gen import generate_scalars
from nabu.backends.python.codegen.writer import write_package
from nabu.config.loader import Config
from nabu.ir.transformer import build_ir

SCHEMA = """
scalar DateTime

enum Status { ACTIVE INACTIVE }

interface Node { id: ID! }

type Author implements Node {
    id: ID!
    name: String!
    createdAt: DateTime!
}

type Book implements Node {
    id: ID!
    title: String!
    status: Status!
    author: Author!
    tags: [String!]!
}

input CreateBookInput {
    title: String!
    authorId: ID!
}

type Query {
    book(id: ID!): Book
    author(id: ID!): Author
}

type Mutation {
    createBook(input: CreateBookInput!): Book!
}
"""

OPERATION = """
query GetBook($id: ID!) {
    book(id: $id) {
        id
        title
        status
        author {
            id
            name
        }
    }
}
"""


@pytest.fixture
def doc():
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [parse(Source(OPERATION, "op.graphql"))]
    return build_ir(schema, docs).value


@pytest.fixture
def cfg():
    return Config(
        schema="schema.graphqls",
        operations="ops/",
        output="out",
        scalars={"DateTime": "datetime.datetime"},
    )


def test_dependency_order_books_after_author(doc):
    order = dependency_order(doc)
    assert order.index("Author") < order.index("Book")


def test_dependency_order_all_types_present(doc):
    order = dependency_order(doc)
    assert "Author" in order and "Book" in order


def test_dependency_order_is_stable(doc):
    assert dependency_order(doc) == dependency_order(doc)


def test_enums_contains_class(doc):
    src = generate_enums(doc)
    assert "class Status(str, Enum)" in src


def test_enums_contains_values(doc):
    src = generate_enums(doc)
    assert 'ACTIVE = "ACTIVE"' in src
    assert 'INACTIVE = "INACTIVE"' in src


def test_enums_deterministic(doc):
    assert generate_enums(doc) == generate_enums(doc)


def test_inputs_contains_class(doc, cfg):
    src = generate_inputs(doc, cfg)
    assert "class CreateBookInput(BaseModel)" in src


def test_inputs_required_field(doc, cfg):
    src = generate_inputs(doc, cfg)
    assert "title: str" in src


def test_inputs_deterministic(doc, cfg):
    assert generate_inputs(doc, cfg) == generate_inputs(doc, cfg)


def test_models_contains_classes(doc, cfg):
    src = generate_models(doc, cfg)
    assert "class Author(BaseModel)" in src
    assert "class Book(BaseModel)" in src


def test_models_enum_relative_import(doc, cfg):
    src = generate_models(doc, cfg)
    assert "from .enums import Status" in src


def test_models_author_before_book(doc, cfg):
    src = generate_models(doc, cfg)
    assert src.index("class Author") < src.index("class Book")


def test_models_deterministic(doc, cfg):
    assert generate_models(doc, cfg) == generate_models(doc, cfg)


def test_operation_result_class(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "class GetBookResult(BaseModel)" in src


def test_operation_nested_class(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "class GetBookBookAuthor(BaseModel)" in src


def test_operation_enum_import(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "from ..enums import Status" in src


def test_operation_nullable_result(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "book: GetBookBook | None" in src


def test_operations_dict_keys(doc, cfg):
    ops = generate_operations(doc, cfg)
    assert "get_book.py" in ops


def test_query_resolves_against_query_root(cfg):
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [
        parse(Source("query GetBook($id: ID!) { book(id: $id) { id } }", "op.graphql"))
    ]
    d = build_ir(schema, docs).value
    op = d.operations[0]
    src = generate_operation(op, d, cfg)
    assert "book: GetBookBook | None" in src


def test_mutation_resolves_against_mutation_root(cfg):
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [
        parse(
            Source(
                "mutation CreateBook($input: CreateBookInput!) { createBook(input: $input) { id title } }",
                "op.graphql",
            )
        )
    ]
    d = build_ir(schema, docs).value
    op = d.operations[0]
    src = generate_operation(op, d, cfg)
    assert "class CreateBookCreateBook(BaseModel)" in src
    assert "create_book: CreateBookCreateBook" in src


def test_scalars_map_present(cfg):
    src = generate_scalars(cfg)
    assert "SCALAR_MAP" in src
    assert '"DateTime"' in src


def test_scalars_annotation_string_present(cfg):
    src = generate_scalars(cfg)
    assert "datetime.datetime" in src


def test_writer_creates_files(tmp_path):
    from nabu.backends.python.codegen.writer import WriteStats
    result = write_package(tmp_path, {"enums.py": "x = 1\n", "ops/a.py": "y = 2\n"})
    assert not result.failed
    assert isinstance(result.value, WriteStats)
    assert result.value.written == 2
    assert result.value.skipped == 0
    assert (tmp_path / "enums.py").read_text() == "x = 1\n"
    assert (tmp_path / "ops" / "a.py").read_text() == "y = 2\n"


def test_writer_skips_identical(tmp_path):
    write_package(tmp_path, {"enums.py": "x = 1\n"})
    mtime = (tmp_path / "enums.py").stat().st_mtime
    result = write_package(tmp_path, {"enums.py": "x = 1\n"})
    assert (tmp_path / "enums.py").stat().st_mtime == mtime
    assert result.value.skipped == 1
    assert result.value.written == 0


def test_writer_overwrites_changed(tmp_path):
    write_package(tmp_path, {"enums.py": "x = 1\n"})
    write_package(tmp_path, {"enums.py": "x = 2\n"})
    assert (tmp_path / "enums.py").read_text() == "x = 2\n"


def test_generated_package_imports(doc, cfg, tmp_path):
    from nabu.backends.python.codegen.client_gen import generate_client
    from nabu.backends.python.codegen.enum_gen import generate_enums
    from nabu.backends.python.codegen.exceptions_gen import generate_exceptions
    from nabu.backends.python.codegen.input_gen import generate_inputs
    from nabu.backends.python.codegen.model_gen import generate_models
    from nabu.backends.python.codegen.operation_gen import generate_operations
    from nabu.backends.python.codegen.transport_gen import generate_transport

    files = {
        "enums.py": generate_enums(doc),
        "inputs.py": generate_inputs(doc, cfg),
        "models.py": generate_models(doc, cfg),
        "transport.py": generate_transport(),
        "exceptions.py": generate_exceptions(),
        "client.py": generate_client(doc, [], cfg),
        "__init__.py": generate_exports(doc),
    }
    for rel, content in generate_operations(doc, cfg).items():
        files[f"operations/{rel}"] = content
    write_package(tmp_path, files)

    pkg_name = "test_generated_pkg"
    spec = importlib.util.spec_from_file_location(
        pkg_name, tmp_path / "__init__.py", submodule_search_locations=[str(tmp_path)]
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = m
    spec.loader.exec_module(m)
    assert hasattr(m, "Status")
    assert hasattr(m, "Author")
    assert hasattr(m, "Client")


def test_university_end_to_end(tmp_path):
    import inspect

    from nabu.config.loader import Config
    from nabu.context import CompilerContext

    config_path = Path("samples/university/nabu.toml")
    if not config_path.exists():
        pytest.skip("university sample not found")

    ctx = CompilerContext(config_path)
    ctx.load()
    ctx.config = Config(
        schema=ctx.config.schema,
        operations=ctx.config.operations,
        output=str(tmp_path),
        scalars=ctx.config.scalars,
    )
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    ir = ctx.build_ir(schema, documents)
    ctx.analyse(ir)
    ctx.generate(ir)

    pkg_name = "university_e2e"
    spec = importlib.util.spec_from_file_location(
        pkg_name, tmp_path / "__init__.py", submodule_search_locations=[str(tmp_path)]
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = m
    spec.loader.exec_module(m)

    assert hasattr(m, "Client")
    client = m.Client(url="http://example.com/graphql")

    methods = [
        n
        for n, _ in inspect.getmembers(m.Client, inspect.isfunction)
        if not n.startswith("_")
    ]
    assert len(methods) == 14, f"expected 14 methods, got {methods}"

    get_student_sig = inspect.signature(client.get_student)
    params = list(get_student_sig.parameters)
    assert params == ["id"], f"get_student should take (id,), got {params}"

    list_courses_sig = inspect.signature(client.list_courses)
    list_params = list(list_courses_sig.parameters)
    assert "filter" in list_params
    assert "limit" in list_params

    assert hasattr(m, "EnrollmentStatus")
    assert hasattr(m, "CourseStatus")


POLY_SCHEMA = """
enum Kind { A B }

type Cat {
    id: ID!
    name: String!
    kind: Kind!
}

type Dog {
    id: ID!
    name: String!
    breed: String
}

union Animal = Cat | Dog

type Query {
    animal(id: ID!): Animal
}
"""

POLY_OPERATION = """
query GetAnimal($id: ID!) {
    animal(id: $id) {
        ... on Cat { id name kind }
        ... on Dog { id name breed }
    }
}
"""


def _poly_ir(tmp_path):
    schema = build_schema(Source(POLY_SCHEMA, "schema.graphqls"))
    op_path = tmp_path / "get_animal.graphql"
    op_path.write_text(POLY_OPERATION)
    docs = [parse(Source(POLY_OPERATION, str(op_path)))]
    return build_ir(schema, docs).value, tmp_path


def test_union_field_generates_discriminated_alias(tmp_path):
    doc, _ = _poly_ir(tmp_path)
    op = doc.operations[0]
    src = generate_operation(
        op, doc, Config(schema="s", operations="o", output="out", scalars={})
    )
    assert "Annotated[" in src
    assert 'Field(discriminator="typename")' in src
    assert "GetAnimalAnimalCat" in src
    assert "GetAnimalAnimalDog" in src
    assert "GetAnimalAnimal = Annotated[" in src


def test_union_member_class_has_typename_field(tmp_path):
    doc, _ = _poly_ir(tmp_path)
    op = doc.operations[0]
    src = generate_operation(
        op, doc, Config(schema="s", operations="o", output="out", scalars={})
    )
    assert 'Literal["Cat"]' in src
    assert 'Literal["Dog"]' in src
    assert 'Field(alias="__typename")' in src


def test_union_member_class_has_model_config(tmp_path):
    doc, _ = _poly_ir(tmp_path)
    op = doc.operations[0]
    src = generate_operation(
        op, doc, Config(schema="s", operations="o", output="out", scalars={})
    )
    assert "model_config = ConfigDict(populate_by_name=True)" in src


def test_non_union_field_unchanged(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "Annotated[" not in src
    assert "discriminator" not in src


def test_discriminated_union_deserialises(tmp_path):
    doc, _ = _poly_ir(tmp_path)
    op = doc.operations[0]
    src = generate_operation(
        op, doc, Config(schema="s", operations="o", output="out", scalars={})
    )

    op_dir = tmp_path / "operations"
    op_dir.mkdir()
    (op_dir / "__init__.py").write_text("")
    (tmp_path / "enums.py").write_text(
        "from __future__ import annotations\nfrom enum import Enum\n\nclass Kind(str, Enum):\n    A = 'A'\n    B = 'B'\n"
    )
    (op_dir / "get_animal.py").write_text(src)

    pkg = "discriminated_test_pkg"
    import types as _types

    root_pkg = _types.ModuleType(pkg)
    root_pkg.__path__ = [str(tmp_path)]
    root_pkg.__package__ = pkg
    sys.modules[pkg] = root_pkg
    ops_pkg = _types.ModuleType(f"{pkg}.operations")
    ops_pkg.__path__ = [str(op_dir)]
    ops_pkg.__package__ = f"{pkg}.operations"
    sys.modules[f"{pkg}.operations"] = ops_pkg

    enums_spec = importlib.util.spec_from_file_location(
        f"{pkg}.enums", tmp_path / "enums.py"
    )
    enums_m = importlib.util.module_from_spec(enums_spec)
    sys.modules[f"{pkg}.enums"] = enums_m
    enums_spec.loader.exec_module(enums_m)

    spec = importlib.util.spec_from_file_location(
        f"{pkg}.operations.get_animal",
        op_dir / "get_animal.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[f"{pkg}.operations.get_animal"] = m
    spec.loader.exec_module(m)

    from pydantic import TypeAdapter

    Animal = m.GetAnimalAnimal
    adapter = TypeAdapter(Animal)

    cat_data = {"__typename": "Cat", "id": "1", "name": "Whiskers", "kind": "A"}
    result = adapter.validate_python(cat_data)
    assert type(result).__name__ == "GetAnimalAnimalCat"
    assert result.id == "1"
    assert result.typename == "Cat"

    dog_data = {"__typename": "Dog", "id": "2", "name": "Rex", "breed": "Labrador"}
    result2 = adapter.validate_python(dog_data)
    assert type(result2).__name__ == "GetAnimalAnimalDog"
    assert result2.typename == "Dog"


def test_list_field_generates_list_annotation(doc, cfg):
    schema = build_schema(
        Source(
            """
    type Tag { label: String! }
    type Book { id: ID! tags: [Tag!]! }
    type Query { book(id: ID!): Book }
    """,
            "s.graphqls",
        )
    )
    op = parse(
        Source(
            "query GetBook($id: ID!) { book(id: $id) { id tags { label } } }",
            "op.graphql",
        )
    )
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert "tags: list[GetBookBookTags]" in src


def test_nullable_list_field_annotation(doc, cfg):
    schema = build_schema(
        Source(
            """
    type Tag { label: String! }
    type Book { id: ID! tags: [Tag!] }
    type Query { book(id: ID!): Book }
    """,
            "s.graphqls",
        )
    )
    op = parse(
        Source(
            "query GetBook($id: ID!) { book(id: $id) { id tags { label } } }",
            "op.graphql",
        )
    )
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert "tags: list[GetBookBookTags] | None" in src


def test_camelcase_field_gets_alias(doc, cfg):
    schema = build_schema(
        Source(
            """
    type Course { courseCode: String! }
    type Query { course: Course }
    """,
            "s.graphqls",
        )
    )
    op = parse(Source("query GetCourse { course { courseCode } }", "op.graphql"))
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert 'alias="courseCode"' in src
    assert "model_config = ConfigDict(populate_by_name=True)" in src


def test_snake_case_field_no_alias(doc, cfg):
    schema = build_schema(
        Source(
            """
    type Item { id: ID! name: String! }
    type Query { item: Item }
    """,
            "s.graphqls",
        )
    )
    op = parse(Source("query GetItem { item { id name } }", "op.graphql"))
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert "alias=" not in src


def test_models_camelcase_field_gets_alias(doc, cfg):
    src = generate_models(doc, cfg)
    assert 'alias="createdAt"' in src
    assert "model_config = ConfigDict(populate_by_name=True)" in src


def test_writer_removes_stale_files(tmp_path):
    write_package(tmp_path, {"a.py": "x = 1\n", "b.py": "y = 2\n"})
    write_package(tmp_path, {"a.py": "x = 1\n"})
    assert (tmp_path / "a.py").exists()
    assert not (tmp_path / "b.py").exists()


def test_writer_oserror_returns_diagnostic(tmp_path):
    from unittest.mock import patch

    from nabu.backends.python.codegen.writer import write_package
    from nabu.diagnostics.codes import ErrorCode

    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        result = write_package(tmp_path, {"x.py": "a = 1\n"})
    assert result.failed
    assert any(d.code == ErrorCode.WRITE_ERROR for d in result.diagnostics)


def test_double_nonnull_wrap_annotation():
    from nabu.backends.python.codegen.fields import wrap_annotation
    from nabu.ir.types import NamedTypeRef, NonNullTypeRef

    double = NonNullTypeRef(inner=NonNullTypeRef(inner=NamedTypeRef(name="Foo")))
    assert wrap_annotation(double, "FooClass") == "FooClass"


def test_top_level_inline_frags_on_non_poly_parent(cfg):
    schema = build_schema(
        Source(
            """
    interface Node { id: ID! }
    type Cat implements Node { id: ID! name: String! }
    type Query { node: Node }
    """,
            "s.graphqls",
        )
    )
    op = parse(
        Source(
            """
    query GetNode {
        node {
            ... on Cat { id name }
        }
    }
    """,
            "op.graphql",
        )
    )
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert "GetNodeNodeCat" in src


def test_inline_fragments_unknown_selection_type():
    from nabu.backends.python.codegen.operation_gen import _inline_fragments

    class UnknownSel:
        pass

    unknown = UnknownSel()
    result = _inline_fragments([unknown], {})
    assert result == [unknown]


def test_exports_include_interfaces_and_unions(doc):
    # exports_gen.py — interfaces (Node) and union aliases render in models.py
    # so they must also be exported from __init__.py, not just objects
    src = generate_exports(doc)
    assert "from .models import Node" in src  # interface, not a plain object


def test_exports_union_alias():
    # Union types render as aliases in models.py — must be exported too
    schema = build_schema(Source("""
    type Cat { name: String! }
    type Dog { name: String! }
    union Animal = Cat | Dog
    type Query { animal: Animal }
    """, "s.graphqls"))
    d = build_ir(schema, []).value
    src = generate_exports(d)
    assert "from .models import Animal" in src


def test_shared_interface_fields_in_all_union_members(cfg):
    # Step 7: fields selected at the interface level must appear in every member class
    schema = build_schema(Source("""
    interface Animal { id: ID! name: String! }
    type Cat implements Animal { id: ID! name: String! lives: Int! }
    type Dog implements Animal { id: ID! name: String! breed: String }
    union Pet = Cat | Dog
    type Query { pet: Pet }
    """, "s.graphqls"))
    op = parse(Source("""
    query GetPet {
        pet {
            ... on Cat { id name lives }
            ... on Dog { id name breed }
        }
    }
    """, "op.graphql"))
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    # shared fields id and name must appear in BOTH member classes
    cat_block = src[src.index("class GetPetPetCat"):src.index("class GetPetPetDog")]
    dog_block = src[src.index("class GetPetPetDog"):]
    assert "id: str" in cat_block
    assert "name: str" in cat_block
    assert "id: str" in dog_block
    assert "name: str" in dog_block


def test_shared_interface_fields_without_repetition_in_fragments(cfg):
    # Fields at interface level only (not repeated inside fragments) also work
    schema = build_schema(Source("""
    interface Node { id: ID! }
    type A implements Node { id: ID! extra: String! }
    type B implements Node { id: ID! other: Int }
    union Thing = A | B
    type Query { thing: Thing }
    """, "s.graphqls"))
    op = parse(Source("""
    query GetThing {
        thing {
            id
            ... on A { extra }
            ... on B { other }
        }
    }
    """, "op.graphql"))
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    # id is a shared field — must appear in both GetThingThingA and GetThingThingB
    assert src.count("id: str") >= 2


def test_two_aliases_of_same_field_get_distinct_python_fields(cfg):
    # Step 8: activeJobs and failedJobs alias the same field — both need their own alias
    schema = build_schema(Source("""
    type JobPage { totalElements: Int! }
    type Query { jobsPaged: JobPage! }
    """, "s.graphqls"))
    op = parse(Source("""
    query Dashboard {
        activeJobs: jobsPaged { totalElements }
        failedJobs: jobsPaged { totalElements }
    }
    """, "op.graphql"))
    d = build_ir(schema, [op]).value
    src = generate_operation(d.operations[0], d, cfg)
    assert 'alias="activeJobs"' in src
    assert 'alias="failedJobs"' in src
    assert "active_jobs:" in src
    assert "failed_jobs:" in src
