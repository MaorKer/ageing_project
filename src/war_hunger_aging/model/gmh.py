from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from war_hunger_aging.model.gm import GMFit, fit_gompertz_makeham, gm_hazard


@dataclass(frozen=True)
class GMHFit:
    a: float
    b: float
    c: float
    h: float
    converged: bool
    rmse_log: float
    rmse_log_adult: float
    n: int
    message: str

    @property
    def mrdt(self) -> float:
        return float(np.log(2.0) / self.b) if self.b > 0 else float("nan")


def hump(age: np.ndarray, *, h: float, mu: float, sigma: float) -> np.ndarray:
    z = (age - mu) / sigma
    return h * np.exp(-0.5 * z * z)


def gmh_hazard(age: np.ndarray, *, a: float, b: float, c: float, h: float, mu: float, sigma: float) -> np.ndarray:
    return gm_hazard(age, a=a, b=b, c=c) + hump(age, h=h, mu=mu, sigma=sigma)


def fit_gompertz_makeham_hump(
    df: pd.DataFrame,
    *,
    age_col: str = "age",
    mx_col: str = "mx",
    adult_age_min: float = 40,
    adult_age_max: float = 89,
    fit_age_min: float = 15,
    fit_age_max: float = 89,
    mu_h: float = 28,
    sigma_h: float = 10,
    min_points: int = 20,
) -> tuple[GMFit, GMHFit]:
    gm = fit_gompertz_makeham(
        df,
        age_col=age_col,
        mx_col=mx_col,
        age_min=adult_age_min,
        age_max=adult_age_max,
    )

    sub = df[[age_col, mx_col]].copy().dropna()
    sub = sub[(sub[age_col] >= fit_age_min) & (sub[age_col] <= fit_age_max)]
    sub = sub[sub[mx_col] > 0]
    if len(sub) < int(min_points):
        gmh = GMHFit(
            a=gm.a,
            b=gm.b,
            c=gm.c,
            h=float("nan"),
            converged=False,
            rmse_log=float("nan"),
            rmse_log_adult=float("nan"),
            n=int(len(sub)),
            message="too_few_points",
        )
        return gm, gmh

    age = sub[age_col].to_numpy(dtype=float)
    mx = sub[mx_col].to_numpy(dtype=float)

    # Warm start (h0 from excess young mortality over GM baseline).
    gm_pred = gm_hazard(age, a=gm.a, b=gm.b, c=gm.c)
    excess = mx - gm_pred
    h0 = float(np.clip(np.nanmax(excess), 1e-12, 1e3))
    theta0 = np.log([max(gm.a, 1e-12), max(gm.b, 1e-12), max(gm.c, 1e-12), h0])

    def residuals(theta: np.ndarray) -> np.ndarray:
        a = float(np.exp(theta[0]))
        b = float(np.exp(theta[1]))
        c = float(np.exp(theta[2]))
        h = float(np.exp(theta[3]))
        pred = gmh_hazard(age, a=a, b=b, c=c, h=h, mu=mu_h, sigma=sigma_h)
        return np.log(mx) - np.log(pred)

    res = least_squares(residuals, theta0, method="trf", max_nfev=6000)
    a, b, c, h = (float(np.exp(x)) for x in res.x)
    r_all = residuals(res.x)
    rmse_all = float(np.sqrt(np.mean(r_all**2))) if r_all.size else float("nan")

    # Adult-only RMSE for comparability.
    adult_mask = (age >= adult_age_min) & (age <= adult_age_max)
    if adult_mask.any():
        r_adult = r_all[adult_mask]
        rmse_adult = float(np.sqrt(np.mean(r_adult**2))) if r_adult.size else float("nan")
    else:
        rmse_adult = float("nan")

    gmh = GMHFit(
        a=a,
        b=b,
        c=c,
        h=h,
        converged=bool(res.success),
        rmse_log=rmse_all,
        rmse_log_adult=rmse_adult,
        n=int(len(sub)),
        message=str(res.message),
    )
    return gm, gmh
