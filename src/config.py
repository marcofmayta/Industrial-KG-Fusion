from pathlib import Path

SEED = 42
BASELINE_START = "2020-02-01"
BASELINE_END = "2020-03-01"
SENSOR_QUANTILE = 0.999
WINDOW_FREQ = "5min"
WINDOW_SCORE_QUANTILE = 0.90
WINDOW_THRESHOLD_QUANTILE = 0.995
MERGE_GAP_MINUTES = 10
MIN_ASSET_RECORDS = 4
TOP_K = (1, 5, 10, 20, 50)
MAX_QUERIES = 1500
BOOTSTRAPS = 500
TEST_SIZE = 0.20
ANALOG = ("TP2", "TP3", "H1", "DV_pressure", "Reservoirs",
          "Oil_temperature", "Motor_current")
DIGITAL = ("COMP", "DV_eletric", "Towers", "MPG", "LPS",
           "Pressure_switch", "Oil_level", "Caudal_impulses")
METROPT_URL = "https://archive.ics.uci.edu/static/public/791/metropt+3+dataset.zip"
METROPT_SOURCE = "https://archive.ics.uci.edu/dataset/791/metropt+3+dataset"
MAINTENANCE_SOURCE = "https://huggingface.co/datasets/Jvachier/industrial-maintenance-synthetic"


def project_root(start=None):
    start = Path.cwd() if start is None else Path(start)
    for path in (start.resolve(), *start.resolve().parents):
        if (path / "src/config.py").exists() and (path / "notebooks").is_dir():
            return path
    raise FileNotFoundError("Run inside the Industrial-KG Fusion repository.")
