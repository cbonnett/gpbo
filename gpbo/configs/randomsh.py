# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

#random search on a test function
import gpbo.core.acquisitions as acquisitions
import gpbo.core.reccomenders as reccomenders
import gpbo.core.objectives as objectives
import gpbo.core.optimize as optimize

import scipy as sp
import os

import os
if not os.path.exists(os.path.join('.','results')):
    os.mkdir('results')
if not os.path.exists(os.path.join('.','results/randomsh')):
    os.mkdir('results/randomsh')
path = 'results/randomsh'
aqfn,aqpara = acquisitions.random
aqpara['lb']=[-1.,-1.]
aqpara['ub']=[1.,1.]

stoppara= {'nmax':50}
stopfn = optimize.nstopfn

reccfn,reccpara = reccomenders.gpmap
reccpara['lb']=aqpara['lb']
reccpara['ub']=aqpara['ub']

cfn = objectives.cf42

ojf = objectives.trivialojf
ojfchar = {'dx':2,'dev':len(aqpara['ev'])}