from graphql import build_schema

from nabu.ir.types import (
    ListTypeRef,
    NamedTypeRef,
    NonNullTypeRef,
    type_ref_from_graphql,
)


def _field_type(sdl: str, field: str):
    schema = build_schema(sdl)
    return schema.type_map["Query"].fields[field].type


def test_named():
    ref = type_ref_from_graphql(_field_type("type Query { a: Int }", "a"))
    assert ref == NamedTypeRef("Int")


def test_non_null():
    ref = type_ref_from_graphql(_field_type("type Query { a: Int! }", "a"))
    assert ref == NonNullTypeRef(NamedTypeRef("Int"))


def test_list():
    ref = type_ref_from_graphql(_field_type("type Query { a: [Int] }", "a"))
    assert ref == ListTypeRef(NamedTypeRef("Int"))


def test_non_null_list_of_non_null():
    ref = type_ref_from_graphql(_field_type("type Query { a: [Int!]! }", "a"))
    assert ref == NonNullTypeRef(ListTypeRef(NonNullTypeRef(NamedTypeRef("Int"))))


def test_nested_list():
    # The flat FieldSymbol form cannot represent this; the recursive TypeRef can.
    ref = type_ref_from_graphql(_field_type("type Query { a: [[Int]] }", "a"))
    assert ref == ListTypeRef(ListTypeRef(NamedTypeRef("Int")))


def test_type_ref_is_hashable():
    # frozen=True — usable as dict keys / in sets during generation
    ref = NonNullTypeRef(NamedTypeRef("Int"))
    assert {ref: 1}[ref] == 1
