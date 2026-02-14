from __future__ import annotations

import numpy as np
import pandas as pd

from war_hunger_aging.model.gmh import fit_gompertz_makeham_hump, gmh_hazard


def test_gmh_recovers_reasonable_params() -> None:
    rng = np.random.default_rng(0)
    ages = np.arange(15, 90, dtype=float)
    true = {"a": 1e-6, "b": 0.09, "c": 5e-4, "h": 2e-3, "mu": 28.0, "sigma": 10.0}
    mx = gmh_hazard(ages, a=true["a"], b=true["b"], c=true["c"], h=true["h"], mu=true["mu"], sigma=true["sigma"])
    mx_noisy = mx * np.exp(rng.normal(0.0, 0.02, size=mx.shape))
    df = pd.DataFrame({"age": ages, "mx": mx_noisy})

    gm, gmh = fit_gompertz_makeham_hump(df, mu_h=true["mu"], sigma_h=true["sigma"])
    assert gmh.converged
    assert np.isfinite(gmh.b)
    assert abs(gmh.b - true["b"]) / true["b"] < 0.25
    assert gmh.h > 0
    assert gmh.c > 0

