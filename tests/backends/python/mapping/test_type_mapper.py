import pytest

from nabu.backends.python.mapping.scalars import scalar_table
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef


@pytest.fixture
def scalars():
    return scalar_table({"DateTime": "datetime.datetime", "URL": "str"})


def test_nullable_named(scalars):
    assert map_type(NamedTypeRef("String"), scalars) == "str | None"


def test_non_null_named(scalars):
    assert map_type(NonNullTypeRef(NamedTypeRef("String")), scalars) == "str"


def test_nullable_list_of_nullable(scalars):
    assert (
        map_type(ListTypeRef(NamedTypeRef("String")), scalars)
        == "list[str | None] | None"
    )


def test_nullable_list_of_non_null(scalars):
    assert (
        map_type(ListTypeRef(NonNullTypeRef(NamedTypeRef("String"))), scalars)
        == "list[str] | None"
    )


def test_non_null_list_of_nullable(scalars):
    assert (
        map_type(NonNullTypeRef(ListTypeRef(NamedTypeRef("String"))), scalars)
        == "list[str | None]"
    )


def test_non_null_list_of_non_null(scalars):
    assert (
        map_type(
            NonNullTypeRef(ListTypeRef(NonNullTypeRef(NamedTypeRef("String")))), scalars
        )
        == "list[str]"
    )


def test_custom_scalar_non_null(scalars):
    assert (
        map_type(NonNullTypeRef(NamedTypeRef("DateTime")), scalars)
        == "datetime.datetime"
    )


def test_custom_scalar_nullable(scalars):
    assert map_type(NamedTypeRef("DateTime"), scalars) == "datetime.datetime | None"


def test_nested_list(scalars):
    ref = ListTypeRef(ListTypeRef(NamedTypeRef("Int")))
    assert map_type(ref, scalars) == "list[list[int | None] | None] | None"


def test_all_builtin_scalars():
    s = scalar_table({})
    assert map_type(NonNullTypeRef(NamedTypeRef("ID")), s) == "str"
    assert map_type(NonNullTypeRef(NamedTypeRef("Int")), s) == "int"
    assert map_type(NonNullTypeRef(NamedTypeRef("Float")), s) == "float"
    assert map_type(NonNullTypeRef(NamedTypeRef("Boolean")), s) == "bool"


def test_object_type_returned_as_name(scalars):
    assert map_type(NonNullTypeRef(NamedTypeRef("Student")), scalars) == "Student"
    assert map_type(NamedTypeRef("Student"), scalars) == "Student | None"


def test_custom_overrides_builtin():
    s = scalar_table({"String": "my_str"})
    assert map_type(NonNullTypeRef(NamedTypeRef("String")), s) == "my_str"
