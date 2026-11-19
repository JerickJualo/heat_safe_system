"""Command-line wrapper for Phase 4 model training."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.ml.train_model import main


if __name__ == "__main__":
    raise SystemExit(main())
