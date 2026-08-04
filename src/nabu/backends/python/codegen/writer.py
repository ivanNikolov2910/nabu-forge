from pathlib import Path

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


def write_package(output_dir: Path, files: dict[str, str]) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    try:
        expected = {Path(rel) for rel in files}

        if output_dir.exists():
            for existing in output_dir.rglob("*.py"):
                relative = existing.relative_to(output_dir)
                if relative not in expected:
                    existing.unlink()

        for rel_path, content in files.items():
            path = output_dir / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_text(encoding="utf-8") == content:
                continue
            path.write_text(content, encoding="utf-8")

    except OSError as e:
        diagnostics.append(
            Diagnostic(
                code=ErrorCode.WRITE_ERROR,
                severity="error",
                message=f"Failed to write generated package: {e}",
            )
        )
    return Result(value=None, diagnostics=diagnostics)
