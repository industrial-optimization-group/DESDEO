
import pickle
from pathlib import Path

import joblib
import skops.io as sio
from sklearn.datasets import make_gaussian_quantiles
from sklearn.linear_model import LogisticRegression

if __name__ == "__main__":
    X, y = make_gaussian_quantiles(n_samples=500, n_features=4, random_state=0)
    gpr = LogisticRegression(
            random_state=0).fit(X, y)
    #gpr.fit(X, y)
    #with Path.open('model2.pkl', 'wb') as file:
    #joblib.dump(gpr, 'model2.pkl')
    sio.dump(gpr, "model2.skops")
