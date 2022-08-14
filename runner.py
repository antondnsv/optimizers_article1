# -*- coding: utf-8 -*-
import os
import sys
from itertools import product
import pandas as pd
import argparse

sys.path.append('./OptimizersArticle')

from data_generator.data_generator import generate_data
from optimizers.optimizers import ScipyModel, PyomoModel
from optimizers.optimization import pricing_optimization

IS_DOCKER = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
if IS_DOCKER:
    STAT_PATH = './data/docker/stat'
    IMAGES_PATH = './images/docker'
else:
    STAT_PATH = './data/local/stat'
    IMAGES_PATH = './images/local'

FILE_STAT = f'{STAT_PATH}/stat.csv'


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("-m", "--mode", required=False, default=False, type=str,
                             help='')
    args_parser.add_argument("-N", "--N", required=False, default=10, type=int,
                             help='Размер задачи')
    args_parser.add_argument("-s", "--seed", required=False, default=42, type=int,
                             help='seed')


    args = vars(args_parser.parse_args())

    data = generate_data(args['N'], seed=args['seed'])

    if args['mode'] == 'pyomo':
        print('запуск модели Pyomo')
        model = pricing_optimization(data, PyomoModel)
        print(model['data'])

    if args['mode'] == 'scipy':
        print('запуск модели Scipy')
        model = pricing_optimization(data, ScipyModel)
        # print(model['data'])
        print(model['status'])
        print(model['message'])

    if args['mode'] == 'compare':

        times = []
        for n in range(10, 255, 5):
            data = generate_data(n, seed=args['seed'])
            model_pyomo_ipopt = pricing_optimization(data, PyomoModel)
            model_scipy_cobyla = pricing_optimization(data, ScipyModel)
            df_pyomo = model_pyomo_ipopt['data'].set_index('plu')
            df_scipy = model_scipy_cobyla['data'].set_index('plu')
            equal_answers = (df_pyomo['x_opt'].round(2) != df_scipy['x_opt'].round(2)).sum() > 0
            P_opt = (df_pyomo['P_opt'].sum().round(3), df_scipy['P_opt'].sum().round(3))
            Q_opt = (df_pyomo['Q_opt'].sum().round(3), df_scipy['Q_opt'].sum().round(3))
            res = (
                n,
                round(model_pyomo_ipopt['t'], 5),
                model_pyomo_ipopt['status'],
                model_pyomo_ipopt['message'],
                round(model_scipy_cobyla['t'], 5),
                model_scipy_cobyla['status'],
                model_scipy_cobyla['message'],
                equal_answers,
                P_opt[0],
                P_opt[1],
                Q_opt[0],
                Q_opt[1],
            )

            print(res)
            times.append(res)

        res = pd.DataFrame(times, columns=['N',
                                           'pyomo_ipopt',
                                           'pyomo_status',
                                           'pyomo_message',
                                           'scipy_cobyla',
                                           'scipy_status',
                                           'scipy_message',
                                           'equal',
                                           'P_opt_pyomo',
                                           'P_opt_scipy',
                                           'Q_opt_pyomo',
                                           'Q_opt_scipy',
                                           ])
        res.to_csv(FILE_STAT, sep='\t', index=False)


    if args['mode'] == 'plot':
        import matplotlib.pyplot as plt

        data = pd.read_csv(FILE_STAT, sep='\t')

        plt.figure(figsize=(12, 6), dpi=100)

        plt.plot(data['N'], data['scipy_cobyla'], lw=2, label='scipy.cobyla')
        plt.plot(data['N'], data['pyomo_ipopt'], lw=2, label='pyomo.ipopt')
        plt.yscale('log')
        plt.legend()
        plt.xlabel('Количество переменных')
        plt.ylabel('Время решения задачи в секундах')
        plt.title('Время решения MINLP задачи через pyomo.bonmin')
        plt.grid()
        plt.savefig(f'{IMAGES_PATH}/solving_time.png')
        plt.show()
