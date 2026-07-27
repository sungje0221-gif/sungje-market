from pathlib import Path
import json, pandas as pd
DATA=Path(__file__).resolve().parents[1]/'data'

def load_json(name,default):
    p=DATA/name
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
    except Exception: return default

def save_json(name,payload):
    (DATA/name).write_text(json.dumps(payload,indent=2),encoding='utf-8')

def load_csv(name,columns):
    p=DATA/name
    try: return pd.read_csv(p) if p.exists() else pd.DataFrame(columns=columns)
    except Exception: return pd.DataFrame(columns=columns)

def save_csv(name,df):
    df.to_csv(DATA/name,index=False)
