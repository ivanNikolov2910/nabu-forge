import importlib.util
import sys
from enum import Enum
from pathlib import Path

import pytest
from graphql import Source, build_schema, parse
from pydantic import BaseModel

from nabu.backends.python.codegen.client_gen import generate_client
from nabu.backends.python.codegen.exceptions_gen import generate_exceptions
from nabu.backends.python.codegen.transport_gen import generate_transport
from nabu.config.loader import Config
from nabu.ir.transformer import build_ir

SCHEMA = """
enum Status { ACTIVE INACTIVE }

type Book {
    id: ID!
    title: String!
}

input CreateBookInput {
    title: String!
}

type Query {
    book(id: ID!): Book
    books(status: Status, limit: Int): [Book!]!
}

type Mutation {
    createBook(input: CreateBookInput!): Book!
}
"""

GET_BOOK = "query GetBook($id: ID!) { book(id: $id) { id title } }"
LIST_BOOKS = "query ListBooks($status: Status, $limit: Int) { books(status: $status, limit: $limit) { id } }"
CREATE_BOOK = "mutation CreateBook($input: CreateBookInput!) { createBook(input: $input) { id } }"


def _generate(op_texts: list[str], tmp_path: Path) -> str:
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    op_files = []
    docs = []
    for i, text in enumerate(op_texts):
        p = tmp_path / f"op{i}.graphql"
        p.write_text(text)
        op_files.append(p)
        docs.append(parse(Source(text, str(p))))
    document = build_ir(schema, docs).value
    config = Config(schema="s", operations="o", output="out", scalars={})
    return generate_client(document, op_files, config)


# ---------------------------------------------------------------------------
# static generators
# ---------------------------------------------------------------------------

def test_transport_contains_class():
    assert "class Transport" in generate_transport()
    assert "httpx" in generate_transport()


def test_exceptions_contains_error():
    src = generate_exceptions()
    assert "class GraphQLResponseError" in src
    assert "class GraphQLClientError" in src


# ---------------------------------------------------------------------------
# client generation
# ---------------------------------------------------------------------------

def test_client_class_and_method(tmp_path):
    src = _generate([GET_BOOK], tmp_path)
    assert "class Client" in src
    assert "async def get_book(self, id: str) -> GetBookResult" in src


def test_document_constant(tmp_path):
    src = _generate([GET_BOOK], tmp_path)
    assert "GET_BOOK_DOCUMENT" in src
    assert "query GetBook" in src


def test_required_before_optional_params(tmp_path):
    src = _generate([LIST_BOOKS], tmp_path)
    # status and limit are both nullable -> both optional with = None
    # (ruff may wrap the signature across lines, so check the fragment)
    assert "status: Status | None = None" in src
    assert "limit: int | None = None" in src


def test_required_param_precedes_optional(tmp_path):
    # $id is required (ID!), $limit is optional (Int) — required must come first
    op = "query Q($id: ID!, $limit: Int) { book(id: $id) { id } }"
    src = _generate([op], tmp_path)
    sig = src.split("async def q(")[1].split(")")[0]
    assert sig.index("id: str") < sig.index("limit: int | None = None")


def test_result_import(tmp_path):
    src = _generate([GET_BOOK], tmp_path)
    assert "from .operations.get_book import GetBookResult" in src


def test_input_import(tmp_path):
    src = _generate([CREATE_BOOK], tmp_path)
    assert "from .inputs import CreateBookInput" in src
    assert "input: CreateBookInput" in src


def test_raises_on_errors(tmp_path):
    src = _generate([GET_BOOK], tmp_path)
    assert "raise GraphQLResponseError" in src
    assert 'response.get("errors")' in src


def test_single_operation_document(tmp_path):
    # Two operations in one file — each document constant must hold only its own op
    src = _generate([GET_BOOK + "\n" + LIST_BOOKS], tmp_path)
    get_book_doc = src.split("GET_BOOK_DOCUMENT")[1].split('"""')[1]
    assert "GetBook" in get_book_doc
    assert "ListBooks" not in get_book_doc


# ---------------------------------------------------------------------------
# serialisation helper (executed from generated source)
# ---------------------------------------------------------------------------

def test_serialize_enum(tmp_path):
    src = _generate([GET_BOOK], tmp_path)
    ns: dict = {"Enum": Enum, "BaseModel": BaseModel}
    # extract and exec just the _serialize function
    start = src.index("def _serialize")
    end = src.index("class Client")
    exec(src[start:end], ns)  # noqa: S102 - trusted generated code in test
    serialize = ns["_serialize"]

    class Color(str, Enum):
        RED = "RED"

    assert serialize(Color.RED) == "RED"
    assert serialize("plain") == "plain"
