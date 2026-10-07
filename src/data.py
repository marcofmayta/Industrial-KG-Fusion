import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import requests

from .config import ANALOG, DIGITAL, METROPT_URL

MISSING_IDS = {"", "-", "NA", "N/A", "NULL", "NONE", "NAN"}
ID_PATTERN = re.compile(r"[A-Z]{1,6}-\d{2,4}[A-Z]?")
NON_ASSET_PREFIXES = {"FOR", "OVER", "UNDER", "AFTER", "BEFORE", "EVERY", "WITH", "AT", "IN", "TO", "FROM"}


def validate_equipment_id(value):
    if pd.isna(value):
        return ""
    value = str(value).strip().upper()
    if value in MISSING_IDS or not ID_PATTERN.fullmatch(value):
        return ""
    return "" if value.split("-")[0] in NON_ASSET_PREFIXES else value


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True,
                                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def download_metropt(raw_dir):
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = raw_dir / "MetroPT3(AirCompressor).csv"
    if csv_path.exists():
        return csv_path
    archive = raw_dir / "metropt3.zip"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        with requests.get(METROPT_URL, stream=True, timeout=120) as response:
            response.raise_for_status()
            with partial.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    stream.write(chunk)
        partial.replace(archive)
    with zipfile.ZipFile(archive) as bundle:
        names = [n for n in bundle.namelist() if Path(n).name == csv_path.name]
        if len(names) != 1:
            raise ValueError("Official archive does not contain exactly one MetroPT CSV.")
        with bundle.open(names[0]) as source, csv_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    return csv_path


def load_metropt(path):
    frame = pd.read_csv(path)
    frame = frame.drop(columns=[c for c in ("Unnamed: 0", "index") if c in frame])
    required = {"timestamp", *ANALOG, *DIGITAL}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing sensor columns: {required - set(frame.columns)}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    if frame["timestamp"].isna().any():
        raise ValueError("Missing sensor timestamps.")
    return frame.sort_values("timestamp", kind="stable").reset_index(drop=True)


def load_maintenance(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("Missing fixed maintenance_sample.parquet. Restore the documented raw snapshot; do not silently resample.")
    frame = pd.read_parquet(path)
    required = {"WorkOrder", "Equipment_ID", "OrderType", "Maintenance_activity_type",
                "WorkOrderDescription", "OperationDescription"}
    if not required.issubset(frame):
        raise ValueError(f"Missing maintenance columns: {required - set(frame.columns)}")
    frame = frame.drop(columns=[c for c in ("combined_text", "text_length") if c in frame])
    frame.insert(0, "row_id", range(len(frame)))
    return frame
