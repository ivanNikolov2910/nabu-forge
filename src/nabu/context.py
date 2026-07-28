from dataclasses import dataclass, field
from pathlib import Path

from graphql import DocumentNode, GraphQLSchema

from nabu.config.loader import Config, load_config
from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.loader.files import list_operation_files, verify_paths
from nabu.model.symbol_table import SymbolTable
from nabu.parser.operations import parse_operations
from nabu.parser.schema import parse_schema


@dataclass
class CompilerContext:
    config_path: Path
    reporter: DiagnosticReporter = field(default_factory=DiagnosticReporter)
    config: Config | None = None

    @property
    def base(self) -> Path:
        return self.config_path.parent

    def load(self) -> Config:
        self.config = self.reporter.collect(load_config(self.config_path))
        return self.config

    def verify(self) -> None:
        self.reporter.collect(verify_paths(self.config, self.base))

    def parse_schema(self) -> GraphQLSchema | None:
        return self.reporter.collect(parse_schema(self.base / self.config.schema))

    def parse_operations(self, schema: GraphQLSchema) -> list[DocumentNode] | None:
        op_files = list_operation_files(self.config, self.base)
        return self.reporter.collect(parse_operations(op_files, schema))

    def build_symbols(
        self, schema: GraphQLSchema, documents: list[DocumentNode]
    ) -> SymbolTable | None:
        return self.reporter.collect(SymbolTable.build(schema, documents))
