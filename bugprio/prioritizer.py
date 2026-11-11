"""
Hybrid bug prioritization.

    final_score = W_RULE * rule_score + W_ML * ml_score       (both in 0..1)

1. Rule-based risk score - transparent, explainable factors:
      exception severity, component criticality, impact (number of failing
      tests), code complexity, critical keywords, and a flakiness discount.
2. ML score - a TF-IDF + Logistic Regression classifier trained on historical
      triaged bugs predicts P1..P4; the class probabilities are converted into
      an expected severity in 0..1.

The final score is mapped to P1 (Critical) .. P4 (Low).
"""
import pickle
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

W_RULE, W_ML = 0.6, 0.4

EXCEPTION_SEVERITY = {
    "PermissionError": 1.0, "MemoryError": 1.0, "RecursionError": 0.9,
    "MissingExceptionHandling": 0.8, "ZeroDivisionError": 0.75, "KeyError": 0.7,
    "TypeError": 0.7, "AttributeError": 0.7, "IndexError": 0.7, "RuntimeError": 0.8,
    "ValueError": 0.55, "AssertionError": 0.5, "TimeoutError": 0.4,
    "ConnectionError": 0.4, "UnknownError": 0.5,
}

COMPONENT_CRITICALITY = {
    "auth": 1.0, "login": 1.0, "security": 1.0, "payment": 1.0, "billing": 1.0,
    "checkout": 0.95, "inventory": 0.8, "database": 0.9, "orders": 0.75,
    "api": 0.65, "calculator": 0.5, "reports": 0.4, "utils": 0.3, "ui": 0.25,
}

CRITICAL_KEYWORDS = {
    "security": 1.0, "password": 0.9, "login": 0.6, "auth": 0.6, "token": 0.7,
    "discount": 0.9, "price": 0.8, "payment": 0.9, "checkout": 0.7, "overcharg": 1.0,
    "negative": 0.6, "duplicate": 0.6, "data loss": 1.0, "crash": 0.7, "corrupt": 0.9,
}

PRIORITY_WEIGHT = {"P1": 1.0, "P2": 0.7, "P3": 0.4, "P4": 0.1}
PRIORITY_NAME = {"P1": "Critical", "P2": "High", "P3": "Medium", "P4": "Low"}

FACTOR_WEIGHTS = {"exception": 0.25, "component": 0.25, "impact": 0.15,
                  "complexity": 0.10, "keywords": 0.25}


def _component_score(module):
    m = module.lower()
    for key, val in COMPONENT_CRITICALITY.items():
        if key in m:
            return val
    return 0.5


def _keyword_score(text):
    t = text.lower()
    hits = [v for k, v in CRITICAL_KEYWORDS.items() if k in t]
    return max(hits) if hits else 0.0


def rule_score(bug, max_tests):
    f = {
        "exception": EXCEPTION_SEVERITY.get(bug.exception_type, 0.5),
        "component": _component_score(bug.module),
        "impact": len(bug.tests) / max_tests if max_tests else 0,
        "complexity": min(bug.complexity / 10.0, 1.0),
        "keywords": _keyword_score(f"{bug.function} {bug.message} {' '.join(bug.tests)}"),
    }
    score = sum(FACTOR_WEIGHTS[k] * v for k, v in f.items())
    reasons = []
    if f["component"] >= 0.8:
        reasons.append(f"critical component '{bug.module}'")
    if f["exception"] >= 0.7:
        reasons.append(f"severe failure type {bug.exception_type}")
    if f["keywords"] >= 0.6:
        reasons.append("security/financial keywords in failure")
    if len(bug.tests) > 1:
        reasons.append(f"breaks {len(bug.tests)} tests")
    if bug.complexity >= 5:
        reasons.append(f"complex code (CC={bug.complexity})")
    if bug.is_flaky:
        reasons.append("FLAKY: passes on re-run (final score x0.6)")
    return round(score, 3), f, reasons


class PriorityModel:
    def __init__(self):
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=2000, C=3.0)),
        ])
        self.metrics = {}

    @staticmethod
    def _text(title, description, component, exc):
        return f"{title} {description} component_{component} exc_{exc}"

    def train(self, csv_path):
        df = pd.read_csv(csv_path).fillna("")
        X = [self._text(r.title, r.description, r.component, r.exception_type) for r in df.itertuples()]
        y = df["priority"].tolist()
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=7, stratify=y)
        self.pipeline.fit(X_tr, y_tr)
        pred = self.pipeline.predict(X_te)
        self.metrics = {
            "accuracy": round(accuracy_score(y_te, pred), 3),
            "report": classification_report(y_te, pred, zero_division=0),
            "n_train": len(X_tr), "n_test": len(X_te),
        }
        self.pipeline.fit(X, y)          # refit on all data for deployment
        return self.metrics

    def predict(self, bug):
        text = self._text(bug.title, bug.description, bug.module, bug.exception_type)
        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        expected = sum(PRIORITY_WEIGHT[c] * p for c, p in zip(classes, probs))
        label = classes[probs.argmax()]
        return round(float(expected), 3), label

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump({"pipeline": self.pipeline, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path):
        m = cls()
        with open(path, "rb") as f:
            d = pickle.load(f)
        m.pipeline, m.metrics = d["pipeline"], d["metrics"]
        return m


def to_priority(score):
    if score >= 0.70:
        return "P1"
    if score >= 0.50:
        return "P2"
    if score >= 0.30:
        return "P3"
    return "P4"


def prioritize(bugs, model):
    max_tests = max((len(b.tests) for b in bugs), default=1)
    for b in bugs:
        b.rule_score, _, b.reasons = rule_score(b, max_tests)
        b.ml_score, b.ml_label = model.predict(b) if model else (b.rule_score, "-")
        b.final_score = round(W_RULE * b.rule_score + W_ML * b.ml_score, 3)
        if b.is_flaky:
            b.final_score = round(b.final_score * 0.6, 3)
        b.priority = to_priority(b.final_score)
    return sorted(bugs, key=lambda b: b.final_score, reverse=True)
