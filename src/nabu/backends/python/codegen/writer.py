from dataclasses import dataclass
from pathlib import Path

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


@dataclass(frozen=True)
class WriteStats:
    written: int
    skipped: int

    @property
    def total(self) -> int:
        return self.written + self.skipped


def write_package(output_dir: Path, files: dict[str, str]) -> Result[WriteStats]:
    diagnostics: list[Diagnostic] = []
    written = skipped = 0
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
                skipped += 1
                continue
            path.write_text(content, encoding="utf-8")
            written += 1

    except OSError as e:
        diagnostics.append(
            Diagnostic(
                code=ErrorCode.WRITE_ERROR,
                severity="error",
                message=f"Failed to write generated package: {e}",
            )
        )
    return Result(value=WriteStats(written=written, skipped=skipped), diagnostics=diagnostics)
