from __future__ import print_function
xrange=range

import scipy as sp
import numpy as np

import gpbo
import os
import matplotlib
from matplotlib import pyplot as plt
plt.style.use('seaborn-paper')
plt.rc('font',serif='Times')

colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
def stoppingplots(path,names,n,legendnames=None,fname='',title='',offset=0.):
    if legendnames==None:
        legendnames=names
    D = dict()
    for name in names:
        D[name]=[]
        for i in range(n):
            D[name].append(gpbo.optimize.readoptdata(os.path.join(path,'{}_{}.csv'.format(name,i))))

    f,a = plt.subplots(1)
    for j,name in enumerate(names):
        gpbo.opts.plotquartsends(a,[D[name][k]['index'] for k in range(n)],[D[name][k]['trueyatxrecc']-offset for k in range(n)],colors[j],0,legendnames[j])

    a.set_yscale('log')
    a.set_xlabel('Steps')
    a.set_ylabel('Regret')
    a.set_title(title)
    a.legend()
    f.savefig(os.path.join(path,'stopping_{}.png'.format(fname)))

    print('tablerow:')
    E=dict()
    for j,name in enumerate(names):
        E[name]=dict()
        E[name]['steps'] = np.empty(n)
        E[name]['endRegret'] = np.empty(n)
        for i in range(n):
            E[name]['steps'][i] = D[name][i]['index'].values[-1]
            E[name]['endRegret'][i] = D[name][i]['trueyatxrecc'].values[-1]-offset
        E[name]['r'] = '{:.3g}'.format(np.mean(E[name]['endRegret']))
        E[name]['s'] = '{:.3g}'.format(np.mean(E[name]['steps']))
        E[name]['rs']= '{:.3g}'.format(np.mean(E[name]['steps']*E[name]['endRegret']))

    print(' & '.join([k for k in names]))
    print(' & '.join([E[k]['r'] for k in names]))
    print(' & '.join([E[k]['s'] for k in names]))
    print(' & '.join([E[k]['rs'] for k in names]))

    return