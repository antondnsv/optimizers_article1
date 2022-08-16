# -*- coding: utf-8 -*-
import os
import sys
from itertools import product
import pandas as pd
import argparse
import matplotlib.pyplot as plt
import seaborn as sns

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
                             help='Режим работы: pyomo/scipy/compare/plot')
    args_parser.add_argument("-N", "--N", required=False, default=10, type=int,
                             help='Количество переменных в задаче')
    args_parser.add_argument("-s", "--seed", required=False, default=42, type=int,
                             help='seed')
    args_parser.add_argument("-gs", "--GRID_SIZE", required=False, default=255, type=int,
                             help='Размер сетки для режима compare (шаг = 5')

    args = vars(args_parser.parse_args())

    data = generate_data(args['N'], seed=args['seed'])

    if args['mode'] == 'pyomo':
        print('запуск модели Pyomo')
        model = pricing_optimization(data, PyomoModel)
        print(model['status'])
        print(model['t'])

    if args['mode'] == 'scipy':
        print('запуск модели Scipy')
        model = pricing_optimization(data, ScipyModel)
        print(model['status'])
        print(model['t'])

    if args['mode'] == 'compare':
        print('запуск расчётов в режиме compare. Внимание, расчёт занимает длительное время!')

        times = []
        for var_num in range(10, args['GRID_SIZE'], 5):
            for iter_num in range(30):
                data = generate_data(var_num, seed=args['seed']+i)
                model_pyomo_ipopt = pricing_optimization(data, PyomoModel)
                model_scipy_cobyla = pricing_optimization(data, ScipyModel)
                df_pyomo = model_pyomo_ipopt['data'].set_index('plu')
                df_scipy = model_scipy_cobyla['data'].set_index('plu')
                equal_answers = (df_pyomo['x_opt'].round(2) != df_scipy['x_opt'].round(2)).sum() > 0
                RTO_opt = ((df_pyomo['Q_opt'] * df_pyomo['P_opt']).sum().round(3),
                           (df_scipy['Q_opt'] * df_scipy['P_opt']).sum().round(3),)
                MARGIN_opt = ((df_pyomo['Q_opt'] * (df_pyomo['P_opt'] - df_pyomo['C'])).sum().round(3),
                              (df_scipy['Q_opt'] * (df_scipy['P_opt'] - df_scipy['C'])).sum().round(3))
                res = (
                    var_num,
                    iter_num,
                    round(model_pyomo_ipopt['t'], 5),
                    model_pyomo_ipopt['status'],
                    model_pyomo_ipopt['message'],
                    round(model_scipy_cobyla['t'], 5),
                    model_scipy_cobyla['status'],
                    model_scipy_cobyla['message'],
                    equal_answers,
                    *RTO_opt,
                    *MARGIN_opt,
                )
                times.append(res)

            print(var_num)

        res = pd.DataFrame(times, columns=['N',
                                           'i',
                                           'pyomo_ipopt',
                                           'pyomo_status',
                                           'pyomo_message',
                                           'scipy_cobyla',
                                           'scipy_status',
                                           'scipy_message',
                                           'equal_answers',
                                           'RTO_pyomo',
                                           'RTO_scipy',
                                           'MARGIN_pyomo',
                                           'MARGIN_scipy',
                                           ])

        res.to_csv(FILE_STAT, sep='\t', index=False)

    if args['mode'] == 'plot':

        data = pd.read_csv(FILE_STAT, sep='\t')

        plt.figure(figsize=(12, 6), dpi=100)

        time_pyomo = data.groupby(['N'])['pyomo_ipopt'].mean()
        time_scipy = data.groupby(['N'])['scipy_cobyla'].mean()
        plt.plot(time_scipy, lw=2, label='scipy.cobyla')
        plt.plot(time_pyomo, lw=2, label='pyomo.ipopt')
        plt.yscale('log')
        plt.legend()
        plt.xlabel('Количество переменных')
        plt.ylabel('Время решения задачи в секундах')
        plt.title('Время решения MINLP задачи через pyomo.bonmin')
        plt.grid()
        plt.savefig(f'{IMAGES_PATH}/solving_time.png')
        plt.show()

        sns.set_style(style="whitegrid")
        plt.figure(figsize=(12, 6), dpi=100)

        margin = data['MARGIN_pyomo'] / data['MARGIN_scipy']
        sales = data['RTO_pyomo'] / data['RTO_scipy']
        margin, sales = 100 * margin, 100 * sales
        sns.scatterplot(margin, sales)
        plt.title('Отношения показателей')
        plt.ylabel('Оборот(pyomo) в % от Оборот(scipy)')
        plt.xlabel('Прибыль(pyomo) в % от Прибыль(scipy)')
        plt.savefig(f'{IMAGES_PATH}/analyze.png')
        plt.show()
