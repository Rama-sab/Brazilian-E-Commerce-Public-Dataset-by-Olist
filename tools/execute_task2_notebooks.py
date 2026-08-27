"""Execute the six Task 2 notebooks sequentially for reproducibility checks."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"
ARTIFACT_DIR = (ROOT / "artifacts").resolve()
NOTEBOOKS = [
    "01_read_and_join.ipynb",
    "02_create_labels.ipynb",
    "03_split_data.ipynb",
    "04_eda_training_only.ipynb",
    "05_feature_engineering.ipynb",
    "06_train_tune_evaluate.ipynb",
]


def clean_artifacts() -> None:
    """Remove only ROOT/artifacts after validating the resolved target."""

    expected = (ROOT / "artifacts").resolve()
    if ARTIFACT_DIR != expected or ROOT.resolve() not in ARTIFACT_DIR.parents:
        raise RuntimeError(f"Refusing to clean unexpected path: {ARTIFACT_DIR}")
    if ARTIFACT_DIR.exists():
        def remove_readonly(function, path, _exc_info):
            """Retry Windows cleanup after making a copied artifact writable."""

            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(ARTIFACT_DIR, onerror=remove_readonly)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove this project's artifacts directory before execution",
    )
    args = parser.parse_args()

    if args.clean:
        clean_artifacts()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # Keep Matplotlib/Jupyter caches within the writable project workspace.
    cache_dir = ROOT / "tmp" / "task2_runtime"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir / "matplotlib"))
    os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(cache_dir / "jupyter"))
    os.environ.setdefault("JUPYTER_CONFIG_DIR", str(cache_dir / "jupyter_config"))
    os.environ.setdefault("IPYTHONDIR", str(cache_dir / "ipython"))
    os.environ.setdefault("PYTHONUTF8", "1")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    started = datetime.now(timezone.utc)
    records: list[dict[str, object]] = []
    for name in NOTEBOOKS:
        path = NOTEBOOK_DIR / name
        if not path.exists():
            raise FileNotFoundError(path)
        print(f"\n=== Executing {name} ===", flush=True)
        notebook = nbformat.read(path, as_version=4)
        t0 = time.perf_counter()
        client = NotebookClient(
            notebook,
            timeout=900,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
            allow_errors=False,
        )
        try:
            client.execute(cwd=str(ROOT))
        finally:
            # Preserve diagnostic output even if a cell fails.
            nbformat.write(notebook, path)
        elapsed = round(time.perf_counter() - t0, 2)
        records.append({"notebook": name, "seconds": elapsed, "status": "ok"})
        print(f"Completed {name} in {elapsed:.2f}s", flush=True)

    log = {
        "status": "success",
        "clean_start": bool(args.clean),
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "notebooks": records,
    }
    (ARTIFACT_DIR / "execution_log.json").write_text(
        json.dumps(log, indent=2), encoding="utf-8"
    )
    print("\nAll six notebooks completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
