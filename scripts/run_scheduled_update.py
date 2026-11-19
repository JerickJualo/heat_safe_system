"""Run the complete HeatSafe refresh pipeline as one scheduled job.

This command is intended for Windows Task Scheduler or an equivalent external
scheduler. It never runs as part of a web request or Django startup.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
LOG_DIR = PROJECT_ROOT / "logs"
LOCK_PATH = PROJECT_ROOT / ".heatsafe_update.lock"
MODEL_ARTIFACTS = [
    PROJECT_ROOT / "models" / "phase4" / "heat_index_next_day_model.joblib",
    PROJECT_ROOT / "models" / "phase4" / "heat_index_multi_horizon_model.joblib",
    PROJECT_ROOT / "data" / "processed" / "ml" / "model_metadata.json",
    PROJECT_ROOT / "data" / "processed" / "ml" / "multi_horizon_model_metadata.json",
]


def _logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"heatsafe_update_{datetime.now():%Y%m%d}.log"
    logger = logging.getLogger("heatsafe_scheduled_update")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


@contextmanager
def _single_instance():
    """Prevent overlapping scheduled runs on Windows and Unix-like systems."""
    lock_file = LOCK_PATH.open("a+")
    lock_file.seek(0)
    lock_file.write("1")
    lock_file.flush()
    try:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError) as exc:
        lock_file.close()
        raise RuntimeError("Another HeatSafe update is already running.") from exc
    try:
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
            try:
                LOCK_PATH.unlink()
            except FileNotFoundError:
                pass


def _run_step(logger: logging.Logger, label: str, *arguments: str) -> None:
    command = [str(PYTHON), *arguments]
    logger.info("Starting: %s", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.stdout:
        logger.info("%s output:\n%s", label, completed.stdout.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}.")
    logger.info("Completed: %s", label)


def _backup_artifacts(backup_dir: Path) -> dict[Path, Path]:
    backups = {}
    for artifact in MODEL_ARTIFACTS:
        if artifact.exists():
            backup = backup_dir / artifact.name
            shutil.copy2(artifact, backup)
            backups[artifact] = backup
    return backups


def _restore_artifacts(backups: dict[Path, Path]) -> None:
    for artifact in MODEL_ARTIFACTS:
        backup = backups.get(artifact)
        if backup is not None:
            shutil.copy2(backup, artifact)
        elif artifact.exists():
            artifact.unlink()


def run() -> int:
    logger = _logger()
    if not PYTHON.exists():
        logger.error("Virtual-environment interpreter not found: %s", PYTHON)
        return 1
    try:
        with _single_instance():
            logger.info("HeatSafe scheduled update started.")
            with tempfile.TemporaryDirectory(prefix="heatsafe_update_", dir=PROJECT_ROOT / "models") as temporary:
                backups = _backup_artifacts(Path(temporary))
                try:
                    _run_step(logger, "historical collection", "scripts/collect_historical_weather.py")
                    _run_step(logger, "preprocessing", "-m", "data_pipeline.preprocessing.run_preprocessing")
                    _run_step(logger, "next-day model training", "scripts/train_heat_index_model.py")
                    _run_step(logger, "one-to-five-day model training", "scripts/train_multi_horizon_model.py")
                    _run_step(logger, "database migrations", "manage.py", "migrate", "--noinput")
                    _run_step(logger, "database import", "manage.py", "import_heatsafe_data")
                except Exception:
                    _restore_artifacts(backups)
                    logger.exception("Update failed; previous model artifacts were restored.")
                    return 1
            logger.info("HeatSafe scheduled update completed successfully.")
    except RuntimeError as exc:
        logger.error("Update skipped: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
