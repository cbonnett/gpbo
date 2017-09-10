import numpy as np
import scipy as sp
import gpbo
from gpbo.core import GPdc
from gpbo.core import objectives
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--index', dest='index', action='store', default=0,type=int)
parser.add_argument('-d', '--dimension', dest='dimension', action='store', default=2,type=int)
args = parser.parse_args()

D = args.dimension
lb = np.array([-1.]*D)
ub = np.array([1.]*D)
#lengthscales from 0.05 to 1.5
lengthscale = [0.2,0.2]
#outputscale will be normalized to 1
fc, xm, truemin = objectives.genmat52ojf(D,lb,ub,A=1.,ls=lengthscale,fixs=-1,ki=GPdc.SQUEXP)

def cfn(sigma):
    return 30*(1e-6)/sigma
def icfn(c):
    return 30*(1e-6)/c

def f(x,**ev):
    y,c,aux = fc(x,**ev)
    return y,cfn(ev['s']),aux

fpath = 'results'
from gpbo.core import debugoutput

import pickle
import time
from scipy.interpolate import interp2d
from scipy.optimize import minimize
from scipy.stats import gamma as gammadist
from scipy.stats import norm
from scipy import stats


def modelp(x, theta):
    return theta[0] + theta[1] * x + theta[2] * x ** 2 + theta[3] * x ** 3  # + theta[4]*x**4

def coef2para(a,order=3,end=200,start=10):
    #convert a poly in a[:order] basic coefficients to value-grad at start and value-grad at end
    b=np.copy(a)

    poly = lambda a,x: np.sum([a[i]*x**float(i) for i in range(order+1)])
    polygrad = lambda a,x: np.sum([float(i)*a[i]*x**float(i-1) for i in range(1,order+1)])
    b[0] = poly(a,start)
    b[1] = polygrad(a,start)
    b[2] = poly(a,end)
    b[3] = polygrad(a,end)
    return b

def extraTp(X,Y,P):
    if len(Y) > 0:
        p0 = Y[0]
    else:
        p0 = 1.
    theta0 = np.array([p0, 0.001, 0.001, P[2][0] * P[2][2] / (200. ** 3), P[4][0] * P[4][2], P[5][0] * P[5][2]])
    def llk(theta):
        theta2 = coef2para(theta)
        pa = 0
        pa += gammadist.logpdf(theta2[0], P[0][0], loc=0, scale=P[0][2])
        pa += norm.logpdf(theta2[1], loc=P[1][0], scale=P[1][1])
        pa += gammadist.logpdf(theta2[2], P[2][0], loc=0., scale=P[2][2])
        pa += gammadist.logpdf(theta2[3], P[3][0], loc=0., scale=P[3][2])
        pa += gammadist.logpdf(theta2[4], P[4][0], loc=0., scale=P[4][2])
        pa += gammadist.logpdf(theta2[5], P[5][0], loc=0., scale=P[5][2])
        L = -pa
        if len(Y)>0:
            Yh = modelp(np.array(X), theta)
            E = Y - Yh
            L -= np.sum(stats.t.logpdf(E, loc=0., scale=theta[4], df=1. / theta[5]))
        return L
    res = minimize(llk, theta0, method='Nelder-Mead')
    return res.x

def overlearn(X,Y,P):
    Theta = extraTp(X,Y,P)
    f = lambda x:modelp(x,Theta)
    return f


def eihyppredictiveaq(optstate,persist,**para):
    t0=time.clock()

    costfn = cfn
    icostfn = icfn
    x,ev,persist,aux = gpbo.core.acquisitions.eihypaq(optstate,persist,**para)
    if optstate.n<para['nrandinit']:
        persist['overhead']=time.clock()-t0
        ev['s'] = icostfn(para['B']/200.)
        return x,ev,persist,aux
    print('-------------------------------------------')
    ev['s'] = 10**-6

    lref,nref,M,V,opara = pickle.load(open('/home/mark/Desktop/paragrid.p','rb'))
    P = pickle.load(open('/home/mark/Desktop/overhead.p','rb'))[0]
    #overhead predictor
    opredict = overlearn(list(range(optstate.n))[para['nrandinit']:],optstate.aqtime[para['nrandinit']:],P)
    OIapprox = lambda x:np.sum([opredict(i) for i in range(para['nrandinit'],x)])
    Oapprox = lambda x:opredict(x)
    #mean-var of regret model
    means = [interp2d(lref,nref,M[i].T) for i in range(len(M))]
    vars  = [interp2d(lref,nref,V[i].T) for i in range(len(V))]
    #hyperparamteres
    A = np.array([h[0] for h in aux['HYPdraws']])
    l = np.array([np.sqrt(h[1]*h[2]) for h in aux['HYPdraws']])

    #noiserange = np.linspace(-8,-4,200)
    nhyp = A.size#len(thetam[0])
    Bgone = sum(optstate.aqtime)+optstate.C
    B = para['B']
    Bremain = B-Bgone

    def nl2thetam(n,l):
        return np.array([p(l,n) for p in means])
    def thetam2r(thetam,m):
        return np.maximum(thetam[0]-thetam[1]*m,thetam[2]-thetam[3]*m)
    def predictR(nsteps,length,noise):
        #takes noise as sigma^2, passes on as log10
        theta = nl2thetam(np.log10(noise),length)
        R = thetam2r(theta,nsteps)
        return R

    #basic sanity check bounds
    sigmamin = icostfn(Bremain) #only take 1 evaluation
    cmax = costfn(sigmamin)
    acc=0
    i=0
    while acc+Oapprox(optstate.n+i)<Bremain:
        acc+=Oapprox(optstate.n+i)
        i+=1
    if i==0:
        #just go for a 1s evaluation since the overhead from this step will take us over budget
        ev['s'] = icostfn(1.)
        print('end on step {} due to budget end')
        return x,ev,persist,aux

    sigmamax = icostfn((Bremain-acc)/i)
    cmin = costfn(sigmamax)
    stepsmax=i
    print('maxcost {} at sigma={}, mincost {} at sigma={} for {} steps'.format(cmax,sigmamin,cmin,sigmamax,i))
    nlevels=100
    N = np.zeros([5,nlevels])
    N[0,:] = np.logspace(np.log10(sigmamin),np.log10(sigmamax),nlevels)
    N[1,:] = costfn(N[0,:])
    for i in range(nlevels):
        acc=0
        nsteps=0
        while acc<=Bremain:
            acc+=N[1,i]+Oapprox(optstate.n+nsteps)
            nsteps+=1
        N[2,i]=nsteps+optstate.n

    s = np.sum([np.log(e['s']) for e in optstate.ev])
    #use the logmean variance under projected policy as noise level to predict performance
    N[3,:] = np.exp(((N[2,:]-optstate.n)*np.log(N[0,:]) + s)/N[2,:])
    for i in range(nlevels):
        for j in range(nhyp):
            N[4,i] += (10**predictR(N[2,i],l[j],N[3,i]))*A[j]/float(nhyp)


    j = np.argmin(N[4,:])
    ev['s'] = N[0,j]
    expectedsteps = N[2,j]
    expectedcost = N[1,j]

    print('expected final regret {} after {} steps. Next ov prediction {} evcost {} meanl {} meanA {} lastover {}'.format(N[4,j],expectedsteps,Oapprox(optstate.n),expectedcost,np.mean(l),np.mean(A),optstate.aqtime[-1]))

    aux['lmean']=np.mean(l)
    aux['steppredict']=expectedsteps
    aux['overpredict']=Oapprox(optstate.n)
    aux['regretpredict']=N[4,j]

    if debugoutput['predictive']:
        from matplotlib import pyplot as plt
        f,a = plt.subplots(nrows=4,ncols=2,figsize=[9,6])
        #a[0,0].plot(np.sort(A),np.linspace(0,1,A.size))

        a[0,0].hist(l,20)
        a[0,1].hist(A,20)
        a[0,1].set_ylabel('A')
        a[0,0].set_ylabel('l')
        a[1,1].semilogx(N[0,:],N[2,:])
        a[1,0].loglog(N[0,:],N[4,:])
        a[3,1].loglog(N[0,:],N[3,:])
        a[2,0].hist([h[1] for h in aux['HYPdraws']],20)
        a[2,1].hist([h[2] for h in aux['HYPdraws']],20)
        plt.savefig('dbout/fig{}.png'.format(optstate.n))
        f.clf()
        plt.close(f)
        del (f)
    #persist['overhead']=time.clock()-t0
    aux['lmean']=np.mean(l)
    return x,ev,persist,aux

for i in range(1):
    fname = 'eihyp{}.csv'.format(i)
    C=gpbo.core.config.eihypdefault(f,D,200,1e-6,fpath,fname)
    C.reccpara['kindex']=C.aqpara['kindex']=GPdc.SQUEXP
    C.reccpara['mprior']=C.aqpara['mprior']= sp.array([0.]+[-1.]*D)
    C.reccpara['sprior']=C.aqpara['sprior']= sp.array([0.5]*(D+1))

    debugoutput['predictive']=True
    C.aqpara['DH_SAMPLES']=250
    C.aqpara['B']=75*cfn(1e-6)
    C.aqfn = eihyppredictiveaq
    C.stopfn = gpbo.optimize.totalTorNstopfn
    C.stoppara['nmax']=200
    C.stoppara['tmax']=C.aqpara['B']
    out = gpbo.search(C)