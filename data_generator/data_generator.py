"""
Генератор данных для задачи ценообразования.
"""
import numpy as np
import pandas as pd

def price_round(prices):
    """
    Округление до ближайшего числа вида XXX.99
    """
    prices_rounded = np.round(prices + 0.01) - 0.01
    return prices_rounded


def generate_data(N: int, seed: int = 0) -> pd.DataFrame:
    """
    Генерация данных для тестирования оптимизационной модели
    """
    np.random.seed(seed)

    data = pd.DataFrame({'plu': range(1, N + 1)})
    data['P'] = price_round((np.random.gamma(2., 3., N) + 4.) * 10.)
    P_mean = data['P'].mean()
    data['E'] = -np.random.gamma(1.7, 0.9, N)
    data['Q'] = np.random.chisquare(5., N) * np.exp(-data['P'] / P_mean)
    data['C'] = round(data['P'] / np.random.normal(1.28, 0.2, N), 2)

    prices_others = price_round(data['P'] * np.random.normal(1.0, 0.2 * np.exp(-data['P'] / P_mean)))
    data['x_lower'] = 0.85 * prices_others / data['P']
    data['x_upper'] = 1.15 * prices_others / data['P']

    data['x_init'] = 0.5 * (data['x_lower'] + data['x_upper'])

    return data
