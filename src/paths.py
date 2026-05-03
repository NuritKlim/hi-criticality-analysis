from pathlib import Path


# Project root = 2 levels up from this file
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Hydroinformed paths
SRC_DIR = PROJECT_ROOT / "src"
INPUT_DIR = SRC_DIR / "Input"
HYDROINF_RESULTS_DIR = SRC_DIR / "Results"
DATA_DIR = SRC_DIR / "Data"