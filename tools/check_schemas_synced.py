"""Pre-commit check: ``schemas/`` is byte-identical to what the models produce.

Runs ``tools.generate_schemas`` into a tempdir, then diffs against the
committed ``schemas/`` directory. Non-destructive — the committed
schemas are read but never written to. Prints an actionable unified diff
when drift is detected.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMITTED_SCHEMAS = REPO_ROOT / "schemas"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        generated = Path(tmpdir) / "schemas"

        gen = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.generate_schemas",
                "--out",
                str(generated),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if gen.returncode != 0:
            sys.stderr.write("schema generation failed:\n")
            sys.stderr.write(gen.stderr)
            return gen.returncode

        diff = subprocess.run(
            ["diff", "-u", "-r", str(COMMITTED_SCHEMAS), str(generated)],
            capture_output=True,
            text=True,
        )
        if diff.returncode != 0:
            sys.stderr.write(
                "schemas/ is out of sync with pydantic_models/.\n"
                "Run `python -m tools.generate_schemas` and commit the result.\n\n"
            )
            sys.stderr.write(diff.stdout)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
