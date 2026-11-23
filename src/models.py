"""Candidatos do experimento: cada um é um Pipeline do scikit-learn.

Todos começam com SimpleImputer(mediana), ajustado só nos dados de treino que o Pipeline recebe.
O StandardScaler entra só nos modelos sensíveis à escala (regressão logística, KNN e MLP).

Suporte a class_weight (desbalanceamento de classes):
- LogisticRegression, DecisionTree, RandomForest: class_weight="balanced".
- AdaBoost: não tem o parâmetro; o estimador-base (stump) usa class_weight="balanced".
- KNN e MLP: não suportam class_weight, ficam sem ponderação.
"""
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src import config

CLASS_WEIGHT_SUPPORT = {
    "logreg": "balanced",
    "knn": "não suporta",
    "tree": "balanced",
    "rf": "balanced",
    "adaboost": "balanced no estimador-base",
    "mlp": "não suporta",
}

DISPLAY_NAMES = {
    "logreg": "LogisticRegression",
    "knn": "KNN",
    "tree": "DecisionTree",
    "rf": "RandomForest",
    "adaboost": "AdaBoost",
    "mlp": "MLP",
}

NEEDS_SCALER = {"logreg", "knn", "mlp"}


def _classifier(name: str):
    seed = config.SEED
    if name == "logreg":
        return LogisticRegression(class_weight="balanced", max_iter=1000, random_state=seed)
    if name == "knn":
        return KNeighborsClassifier(n_neighbors=25, weights="distance", n_jobs=-1)
    if name == "tree":
        return DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, class_weight="balanced", random_state=seed)
    if name == "rf":
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", n_jobs=-1,
                                      random_state=seed)
    if name == "adaboost":
        base = DecisionTreeClassifier(max_depth=1, class_weight="balanced", random_state=seed)
        return AdaBoostClassifier(estimator=base, n_estimators=200, learning_rate=0.5, random_state=seed)
    if name == "mlp":
        return MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=200, random_state=seed)
    raise ValueError(f"modelo desconhecido: {name}")


def candidate_names() -> list[str]:
    return list(CLASS_WEIGHT_SUPPORT)


def build_model(name: str) -> Pipeline:
    """Pipeline SimpleImputer(mediana) [+ StandardScaler] + classificador."""
    etapas = [("imputer", SimpleImputer(strategy="median"))]
    if name in NEEDS_SCALER:
        etapas.append(("scaler", StandardScaler()))
    etapas.append(("clf", _classifier(name)))
    return Pipeline(etapas)
