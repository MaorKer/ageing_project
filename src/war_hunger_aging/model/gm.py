from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


@dataclass(frozen=True)
class GMFit:
    a: float
    b: float
    c: float
    converged: bool
    rmse_log: float
    n: int
    message: str

    @property
    def mrdt(self) -> float:
        return float(np.log(2.0) / self.b) if self.b > 0 else float("nan")


def gm_hazard(age: np.ndarray, *, a: float, b: float, c: float) -> np.ndarray:
    return c + a * np.exp(b * age)


def _initial_guess(age: np.ndarray, mx: np.ndarray) -> tuple[float, float, float]:
    # Simple log-linear guess (ignores c); clamp to keep stable.
    y = np.log(np.clip(mx, 1e-12, None))
    x = age.astype(float)
    x_mean = x.mean()
    y_mean = y.mean()
    denom = np.sum((x - x_mean) ** 2)
    slope = float(np.sum((x - x_mean) * (y - y_mean)) / denom) if denom > 0 else 0.08
    slope = float(np.clip(slope, 1e-4, 1.0))
    intercept = float(y_mean - slope * x_mean)
    a0 = float(np.clip(np.exp(intercept), 1e-12, 1e6))
    b0 = slope
    c0 = float(np.clip(np.min(mx) * 0.1, 1e-12, 1e2))
    return a0, b0, c0


def fit_gompertz_makeham(
    df: pd.DataFrame,
    *,
    age_col: str = "age",
    mx_col: str = "mx",
    age_min: float = 40,
    age_max: float = 89,
) -> GMFit:
    sub = df[[age_col, mx_col]].copy()
    sub = sub.dropna()
    sub = sub[(sub[age_col] >= age_min) & (sub[age_col] <= age_max)]
    sub = sub[sub[mx_col] > 0]
    if len(sub) < 10:
        return GMFit(a=float("nan"), b=float("nan"), c=float("nan"), converged=False, rmse_log=float("nan"), n=int(len(sub)), message="too_few_points")

    age = sub[age_col].to_numpy(dtype=float)
    mx = sub[mx_col].to_numpy(dtype=float)
    a0, b0, c0 = _initial_guess(age, mx)
    theta0 = np.log([a0, b0, c0])

    def residuals(theta: np.ndarray) -> np.ndarray:
        a = float(np.exp(theta[0]))
        b = float(np.exp(theta[1]))
        c = float(np.exp(theta[2]))
        pred = gm_hazard(age, a=a, b=b, c=c)
        return np.log(mx) - np.log(pred)

    res = least_squares(residuals, theta0, method="trf", max_nfev=4000)
    a, b, c = (float(np.exp(x)) for x in res.x)
    r = residuals(res.x)
    rmse = float(np.sqrt(np.mean(r**2))) if r.size else float("nan")
    return GMFit(a=a, b=b, c=c, converged=bool(res.success), rmse_log=rmse, n=int(len(sub)), message=str(res.message))

