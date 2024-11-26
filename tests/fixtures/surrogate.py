"""Make temporary directories and files for two surrogate models for testing."""

import joblib
import pytest
#import skops.io as sio
from sklearn.datasets import make_friedman2, make_gaussian_quantiles
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, WhiteKernel
from sklearn.linear_model import LogisticRegression


@pytest.fixture
def surrogate_file(tmp_path):
    X, y = make_friedman2(n_samples=500, noise=0, random_state=0)
    kernel = DotProduct() + WhiteKernel()
    gpr = GaussianProcessRegressor(kernel=kernel,
            random_state=0).fit(X, y)
    fn = tmp_path / "surr/model.pkl"
    fn.parent.mkdir()
    fn.touch()
    joblib.dump(gpr, fn)
    return fn
    #sio.dump(gpr, "model.skops")

@pytest.fixture
def surrogate_file2(tmp_path):
    X, y = make_gaussian_quantiles(n_samples=500, n_features=4, random_state=0)
    lr = LogisticRegression(
            random_state=0).fit(X, y)
    fn = tmp_path / "surr2/model2.pkl"
    fn.parent.mkdir()
    fn.touch()
    joblib.dump(lr, fn)
    return fn
    #sio.dump(lr, "model2.skops")
