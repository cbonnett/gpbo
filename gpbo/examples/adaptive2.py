import matplotlib
#matplotlib.use('Agg')

import gpbo
from gpbo.core import objectives as objectives
from gpbo.core import GPdc as GPdc
import os
import scipy as sp
import time

gpbo.core.debugoutput=True
gpbo.core.debugoptions={'datavis':True,'drawlap':False,'cost1d':False,'ctaq':False,'support':False,'adaptive':True,'logstate':True}

D=2
n=50
s=1e-12

lb=[-1.,-1.]
ub = [1.,1.]

f, xmin, ymin = objectives.genmat52ojf(D,lb,ub,ls=0.20,fixs=-1)
if True:
    with open('results/adaptive.txt','w') as o:
        o.write('reported truemin x {} ; y {}'.format(xmin,ymin))

    gpbo.core.ESutils.plot2dFtofile(f,os.path.join('dbout', 'truegeneratedobjective' + time.strftime('%d_%m_%y_%H:%M:%S') + '.png'),xmin=xmin)

class conf():
    """
        fixed s, space is [-1,1]^D

        """

    def __init__(self, f, D, n, s, path, fname):


        C = gpbo.core.config.pesfsdefault(f, D, 10, s, 'results', 'introspection.csv')
        #C = gpbo.core.config.eimledefault(f,D,10,s,'results','introspection.csv')
        aq0 = C.aqfn
        aq0para = C.aqpara

        aq1 = gpbo.core.acquisitions.splocalaq
        aq1para = {
            'ev': {'s': s, 'd': [sp.NaN]},
            'lb': [-1.] * D,
            'ub': [1.] * D,
            'start': [0.] * D
        }

        self.chooser = gpbo.core.choosers.introspection
        self.choosepara = {
            'ev': aq0para['ev'],
            'lb': aq0para['lb'],
            'ub': aq0para['ub'],
            'mprior': aq0para['mprior'],
            'sprior': aq0para['sprior'],
            'kindex': aq0para['kindex'],
            'nhyp' : 12,
            'maxf': 20000,
            'onlyafter': aq0para['nrandinit'],
            'check': True,
            'everyn': 1,
            'support': 1500,
            'draws': 8000,
            'starts': 20,
            'cheatymin': ymin,
            'cheatf': f,
            'regretswitch':1e-4,
            'budget': n
        }
        #self.chooser = gpbo.core.choosers.aftern
        #self.choosepara = {'n':12}
        self.aqfn = [aq0,aq1]
        self.aqpara = [aq0para,aq1para]
        self.multimode = True

        self.stoppara = {'nmax': n}
        self.stopfn = gpbo.core.optimize.norlocalstopfn

        reccfn0 = C.reccfn
        reccpara0 = C.reccpara
        reccpara0['smode']='dthenl'
        reccfn1 = gpbo.core.reccomenders.argminrecc
        reccpara1 = {'check': True}

        self.reccfn = [reccfn0,reccfn1]
        self.reccpara = [reccpara0,reccpara1]

        self.ojfchar = {'dx': len(aq0para['lb']), 'dev': len(aq0para['ev'])}
        self.ojf = f

        self.path = path
        self.fname = fname
        return
C = conf(f,D,341,s,'results','adaptive.csv')

out = gpbo.search(C,initdata=False)

