"""
Online Logistic Regression with stochastic gradient descent.
Pure Python, no numpy/scipy. Updates weights after each new outcome.
Features are standardized online using running mean and variance.
"""
import math
import json
import os

class OnlineLogisticRegression:
    def __init__(self, feature_names, learning_rate=0.01, l2=0.001):
        self.feature_names = feature_names
        self.n_features = len(feature_names)
        self.lr = learning_rate
        self.l2 = l2
        self.weights = [0.0] * self.n_features
        self.bias = 0.0
        # Online standardization: count, mean, M2 for each feature
        self.count = 0
        self.mean = [0.0] * self.n_features
        self.m2 = [0.0] * self.n_features

    def _standardize(self, features):
        """Return z-scores using online mean/variance."""
        if self.count < 2:
            return list(features)
        z = []
        for i, x in enumerate(features):
            if self.m2[i] <= 0:
                z.append(0.0)
            else:
                variance = self.m2[i] / (self.count - 1)
                std = math.sqrt(variance) + 1e-8
                z.append((x - self.mean[i]) / std)
        return z

    def _update_running_stats(self, features):
        self.count += 1
        for i, x in enumerate(features):
            delta = x - self.mean[i]
            self.mean[i] += delta / self.count
            delta2 = x - self.mean[i]
            self.m2[i] += delta * delta2

    def _sigmoid(self, z):
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        else:
            ez = math.exp(z)
            return ez / (1.0 + ez)

    def predict_proba(self, features):
        """Return probability of positive class (pump)."""
        z = self.bias
        z_features = self._standardize(features)
        for i, x in enumerate(z_features):
            z += self.weights[i] * x
        return self._sigmoid(z)

    def update(self, features, label, update_stats=True):
        """
        Update model weights with one training example.
        label: 0 for rug/no pump, 1 for pump.
        """
        if update_stats:
            self._update_running_stats(features)
        z_features = self._standardize(features)
        prob = self.predict_proba(features)  # uses current stats
        error = prob - label
        # SGD update
        for i, x in enumerate(z_features):
            grad = error * x + self.l2 * self.weights[i]
            self.weights[i] -= self.lr * grad
        self.bias -= self.lr * error

    def save(self, path):
        data = {
            "feature_names": self.feature_names,
            "weights": self.weights,
            "bias": self.bias,
            "count": self.count,
            "mean": self.mean,
            "m2": self.m2,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            data = json.load(f)
        model = cls(data["feature_names"])
        model.weights = data["weights"]
        model.bias = data["bias"]
        model.count = data["count"]
        model.mean = data["mean"]
        model.m2 = data["m2"]
        return model

# Feature names (must match stored token data)
FEATURE_NAMES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]

MODEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ml_model.json")

def get_model():
    if os.path.exists(MODEL_FILE):
        return OnlineLogisticRegression.load(MODEL_FILE)
    else:
        return OnlineLogisticRegression(FEATURE_NAMES)

def train_model(features: dict, label: int):
    """Update model with one sample (label 0 or 1)."""
    model = get_model()
    feature_list = [features.get(name, 0.0) for name in FEATURE_NAMES]
    model.update(feature_list, label)
    model.save(MODEL_FILE)
    return model

def predict_pump_probability(features: dict) -> float:
    """Return probability of pump for given token features."""
    model = get_model()
    if model.count < 10:
        return 0.5  # not enough training data
    feature_list = [features.get(name, 0.0) for name in FEATURE_NAMES]
    return model.predict_proba(feature_list)
