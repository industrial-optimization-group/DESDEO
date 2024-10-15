
import pickle
from pathlib import Path

import joblib
import skops.io as sio
from sklearn.datasets import make_friedman2, make_gaussian_quantiles
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, WhiteKernel

if __name__ == "__main__":
    X, y = make_friedman2(n_samples=500, noise=0, random_state=0)
    kernel = DotProduct() + WhiteKernel()
    gpr = GaussianProcessRegressor(kernel=kernel,
            random_state=0).fit(X, y)
    #gpr.fit(X, y)
    #with Path.open('model.pkl', 'wb') as file:
    #joblib.dump(gpr, 'model.pkl')
    #joblib.dump(gpr, 'model.sav')
    sio.dump(gpr, "model.skops")
