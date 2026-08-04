from dataclasses import dataclass, field
from pathlib import Path

from graphql import DocumentNode, GraphQLSchema

from nabu.analysis.analyser import analyse
from nabu.config.loader import Config, load_config
from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.ir.document import IRDocument
from nabu.ir.transformer import build_ir
from nabu.loader.files import list_operation_files, verify_paths
from nabu.log import logger
from nabu.parser.operations import parse_operations
from nabu.parser.schema import parse_schema


@dataclass
class CompilerContext:
    config_path: Path
    reporter: DiagnosticReporter = field(default_factory=DiagnosticReporter)
    config: Config = field(init=False)

    @property
    def base(self) -> Path:
        return self.config_path.parent

    def load(self) -> Config:
        logger.info("Loading %s", self.config_path)
        self.config = self.reporter.collect(load_config(self.config_path))
        return self.config

    def verify(self) -> None:
        logger.info("Verifying schema and operations paths")
        self.reporter.collect(verify_paths(self.config, self.base))

    def parse_schema(self) -> GraphQLSchema:
        schema_path = self.base / self.config.schema
        logger.info("Parsing schema: %s", schema_path)
        return self.reporter.collect(parse_schema(schema_path))

    def parse_operations(self, schema: GraphQLSchema) -> list[DocumentNode]:
        op_files = list_operation_files(self.config, self.base)
        logger.info("Parsing %d operation file(s)", len(op_files))
        return self.reporter.collect(parse_operations(op_files, schema))

    def build_ir(
        self, schema: GraphQLSchema, documents: list[DocumentNode]
    ) -> IRDocument:
        logger.info("Building IR")
        return self.reporter.collect(build_ir(schema, documents))

    def analyse(self, document: IRDocument) -> IRDocument:
        logger.info("Running semantic analysis")
        return self.reporter.collect(analyse(document, self.config))

    def generate(self, document: IRDocument) -> None:
        from nabu.backends.python.codegen.client_gen import generate_client
        from nabu.backends.python.codegen.enum_gen import generate_enums
        from nabu.backends.python.codegen.exceptions_gen import generate_exceptions
        from nabu.backends.python.codegen.exports_gen import generate_exports
        from nabu.backends.python.codegen.input_gen import generate_inputs
        from nabu.backends.python.codegen.model_gen import generate_models
        from nabu.backends.python.codegen.operation_gen import generate_operations
        from nabu.backends.python.codegen.scalars_gen import generate_scalars
        from nabu.backends.python.codegen.transport_gen import generate_transport
        from nabu.backends.python.codegen.writer import write_package

        op_files = list_operation_files(self.config, self.base)
        output = self.base / self.config.output

        logger.info(
            "Generating Python package: %d enums, %d inputs, %d models, %d operations",
            len(document.enums),
            len(document.inputs),
            len(document.objects),
            len(document.operations),
        )
        ops = generate_operations(document, self.config)
        files: dict[str, str] = {
            "enums.py": generate_enums(document),
            "inputs.py": generate_inputs(document, self.config),
            "models.py": generate_models(document, self.config),
            "scalars.py": generate_scalars(self.config),
            "transport.py": generate_transport(),
            "exceptions.py": generate_exceptions(),
            "client.py": generate_client(document, op_files, self.config),
            "__init__.py": generate_exports(document),
        }
        for rel_path, content in ops.items():
            files[f"operations/{rel_path}"] = content

        logger.info("Writing %d files to %s", len(files), output)
        self.reporter.collect(write_package(output, files))
