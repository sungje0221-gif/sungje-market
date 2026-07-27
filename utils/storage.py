from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def load_json(name, default):
    path = DATA / name
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def save_json(name, payload):
    (DATA / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

def load_csv(name, columns):
    path = DATA / name
    if not path.exists(): return pd.DataFrame(columns=columns)
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame(columns=columns)

def save_csv(name, df):
    df.to_csv(DATA / name, index=False)
