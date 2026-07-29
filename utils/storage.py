from pathlib import Path
import json,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def load_json(name,default):
    p=DATA/name
    if not p.exists():return default
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return default

def save_json(name,payload):
    (DATA/name).write_text(json.dumps(payload,indent=2),encoding="utf-8")

def load_csv(name,columns):
    p=DATA/name
    if not p.exists():return pd.DataFrame(columns=columns)
    try:return pd.read_csv(p)
    except:return pd.DataFrame(columns=columns)

def save_csv(name,df):
    df.to_csv(DATA/name,index=False)
