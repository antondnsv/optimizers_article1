"""
Классы оптимизаторов.
"""
from typing import Dict
import abc
import numpy as np
from scipy.optimize import NonlinearConstraint, LinearConstraint, minimize
import pyomo.environ as pyo


class OptimizationModel(abc.ABC):
    """
    Базовый класс для оптимизаторов с ЦО
    """

    def __init__(self, data):

        self.data = data.copy()
        self.plu_idx = data['sku'].index

        self.N = self.data['sku'].nunique()
        self.P = self.data['P'].values
        self.Q = self.data['Q'].values
        self.E = self.data['E'].values
        self.C = self.data['C'].values

        # границы для индексов
        self.x_lower = np.array(self.data['x_lower'].values, dtype=float)
        self.x_upper = np.array(self.data['x_upper'].values, dtype=float)
        self.x_init = (0.5 * (data['x_lower'] + data['x_upper'])).values

        self.m_min = sum(self.data['Q'] * (self.data['P'] - self.data['C']))


    @abc.abstractmethod
    def init_objective(self):
        """
        Инициализация целевой функции - выручка
        """

    @abc.abstractmethod
    def init_constraints(self):
        """
        Инициализация ограничений
        """

    @abc.abstractmethod
    def solve(self) -> Dict:
        """
        Метод, запускающий решение поставленной оптимизационной задачи
        """


class ScipyModel(OptimizationModel):
    """
    Класс, который создаёт NLP оптимизационную модель на базе библиотеки scipy
    """

    def __init__(self, data):
        super().__init__(data)

        # Задаём объект для модели scipy
        self.obj = None
        self.constraints = []

    def _el(self, E, x):
        return np.exp(E * (x - 1.0))

    def init_objective(self):
        def objective(x):
            return -sum(self.P * x * self.Q * self._el(self.E, x))

        self.obj = objective

    def init_constraints(self):

        A = np.eye(self.N, self.N, dtype=float)
        bounds = LinearConstraint(A, self.x_lower, self.x_upper)
        self.constraints.append(bounds)

        def con_mrg(x):
            con_mrg_expr = sum((self.P * x - self.C) * self.Q * self._el(self.E, x))
            return con_mrg_expr
        constr = NonlinearConstraint(con_mrg, self.m_min, np.inf)
        self.constraints.append(constr)

    def solve(self):

        result = minimize(self.obj, self.x_init, method='cobyla', constraints=self.constraints)

        self.data['x_opt'] = result['x']
        self.data['P_opt'] = self.data['x_opt'] * self.data['P']
        self.data['Q_opt'] = self.Q * self._el(self.E, self.data['x_opt'])

        return {
            'message': str(result['message']),
            'status': str(result['status']),
            'model': result,
            'data': self.data
        }


class PyomoModel(OptimizationModel):
    """
    Класс, который создаёт NLP оптимизационную модель на базе библиотеки PYOMO
    """

    def __init__(self, data):
        super().__init__(data)

        # Задаём объект модели pyomo
        self.model = pyo.ConcreteModel()

    def _el(self, i):
        # вспомогательная функция для пересчета спроса при изменении цены
        return pyo.exp(self.E[i] * (self.model.x[i] - 1.0))

    def init_objective(self):

        def bounds_fun(model, i):
            return self.x_lower[i], self.x_upper[i]

        def init_fun(model, i):
            return self.x_init[i]

        self.model.x = pyo.Var(range(self.N), domain=pyo.Reals, bounds=bounds_fun, initialize=init_fun)
        self.model.con_equal = pyo.Constraint(pyo.Any)

        objective = sum(self.P[i] * self.model.x[i] * self.Q[i] * self._el(i) for i in range(self.N))
        self.model.obj = pyo.Objective(expr=objective, sense=pyo.maximize)

    def init_constraints(self):
        con_mrg_expr = sum((self.P[i] * self.model.x[i] - self.C[i]) * self.Q[i] * self._el(i)
                           for i in range(self.N)) >= self.m_min
        self.model.con_mrg = pyo.Constraint(rule=con_mrg_expr)

    def solve(self):

        solver = pyo.SolverFactory('ipopt', tee=False)

        result = solver.solve(self.model)

        self.data['x_opt'] = [self.model.x[i].value for i in self.model.x]
        self.data['P_opt'] = self.data['x_opt'] * self.data['P']
        self.data['Q_opt'] = [self.Q[i] * pyo.value(self._el(i)) for i in self.model.x]

        return {
            'message': str(result.solver.termination_condition),
            'status': str(result.solver.status),
            'model': self.model,
            'data': self.data
        }
