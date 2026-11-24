"""Acrescenta a persistência na VALIDAÇÃO a models/model_meta.json (o dashboard mostra RF x persistência).
Só usa treino e validação; o teste continua intocado. Uso: python scripts/patch_meta_persistencia.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src.evaluate import persistence_baseline
from src.features import build_features, load_inputs
from src.train import locked_split

meta = json.loads(config.MODEL_META_PATH.read_text(encoding="utf-8"))
panel, clima = load_inputs()
city = any(f.startswith("cidade_") for f in meta["features"])
split = locked_split(build_features(panel, clima, city=city))
pers = persistence_baseline(split.val, tuple(meta["thresholds"]))
meta["validation_metrics"]["persistencia_f1_macro"] = pers["f1_macro"]
meta["validation_metrics"]["persistencia_recall_alto"] = pers["recall_alto"]
config.MODEL_META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print("persistência na validação:", round(pers["f1_macro"], 3), "F1-macro;", round(pers["recall_alto"], 3), "recall alto")
