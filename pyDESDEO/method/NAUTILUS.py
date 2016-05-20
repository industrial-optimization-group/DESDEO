# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
NAUTILUS method variants

NAUTILUS    The first NAUTILUS variant by Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.

TODO
----
Longer description of the method variants and methods
'''
import numpy as np
from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.metrics import pairwise_distances_argmin_min

from problem.Problem import Problem
from result.Result import IterationPoint
from core.ResultFactory import IterationPointFactory, BoundsFactory
from optimization.OptimizationProblem import AchievementProblem, \
    EpsilonConstraintProblem

from Method import Method


def printCurrentIteration(method):
        print "Iteration %s/%s" % (method.user_iters - method.current_iter, method.user_iters)
        print "DISTANCE: ", method.distance()
        print "Iteration point:", method.zh
        print "Lower boundary:", method.fh_lo
        print "=============================="


class NAUTILUS(Method):
    
    def __init__(self,problem,method_class):
        self.problem = problem
        self.method_class = method_class
        self.user_iters = 5
        self.current_iter = self.user_iters
        self.fh_factory = IterationPointFactory(self.method_class(AchievementProblem(self.problem)))
        self.bounds_factory = BoundsFactory(self.method_class(EpsilonConstraintProblem(self.problem)))
        self.preference = None

        self.fh_lo, self.zh = tuple(self.problem.objective_bounds())
        self.fh = self.fh_lo
        self.zh_prev=self.zh

        # self.zh = self.zh_pref = self.fh = self.fh_lo = None

    def _update_fh(self):
        self.fh = list(self.fh_factory.result(self.preference, self.zh_prev))

    def _next_zh(self,term1,term2):
        return list((self.current_iter - 1.) / self.current_iter * np.array(term1) + (1. / self.current_iter) * np.array(term2))
    def _update_zh(self,term1,term2):
        self.zh_prev = self.zh

        self.zh = self._next_zh(term1,term2)



class ENAUTILUS(NAUTILUS):
    def __init__(self, problem, method_class):
        '''
        Constructor
        '''
        super(ENAUTILUS,self).__init__(problem,method_class)
        self.Ns = 5
    

    def printCurrentIteration(self):
        print "Iteration %s/%s\n" % (self.user_iters - self.current_iter, self.user_iters)
        
        for pi,ns_point in enumerate(self.NsPoints):
            print "Ns %i"%(pi+1)
            print "Iteration point:", self.zhs[pi]
            print "Lower boundary: ", self.zh_los[pi]
            print "Closeness: ", self.distance(self.zhs[pi],ns_point)
        print "=============================="

    def _update_zh(self,term1,term2):

        return self._next_zh(term1, term2)

    
    def select_point(self,point):
        pass
    
    
    def nextIteration(self, preference=None):
        '''
        Return next iteration bounds
        '''

        points=np.array(self.problem.points)
        # Reduce point set if starting from DM specified sol
        if preference is not None:
            points=points[(np.any(points > preference[1],axis=1) & np.any(points < preference[0],axis=1))]
            #points=points[np.any(points>np.array(preference[0]==False),axis=1)]
            #points=points[np.any(points<np.array(preference[1]==False),axis=1)]
            self.zh=preference[1]

        if len(points)<=self.Ns:
            print "Only %s points can be reached from selected iteartion point"%len(points)
            self.NsPoints=points
        else:      
            k_means = KMeans(n_clusters=self.Ns)
            k_means.fit(points)
            
            closest, _ = pairwise_distances_argmin_min(k_means.cluster_centers_, points)
            
            self.NsPoints = map(list,points[closest])

        self.zh_los=[]
        self.zhs=[]
        for point in self.NsPoints:
            self.zhs.append(self._update_zh(self.zh_prev,point))
            #self.fh=point
            self.fh_lo = list(self.bounds_factory.result(self.zhs[-1]))
            self.zh_los.append(self.fh_lo)
            
 

        self.zh_prev=self.zh
        self.current_iter -= 1

        return zip(self.zh_los,self.zhs)



class NAUTILUSv1(NAUTILUS):
    '''
    The first NAUTILUS method variant[1]_

    References
    ----------

    [1] Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.,
        NAUTILUS method: An interactive technique in multiobjective optimization based on the nadir point,
        European Journal of Operational Research, 2010 , 206 , 426-434.
    '''
    def printCurrentIteration(self):
            print "Iteration %s/%s" % (self.user_iters - self.current_iter, self.user_iters)
            print "DISTANCE: ", self.distance()
            print "Iteration point:", self.zh
            print "Lower boundary:", self.fh_lo
            print "=============================="


    def __init__(self, problem, method_class):
        '''
        Constructor
        '''
        super(NAUTILUSv1,self).__init__(problem,method_class)


    def nextIteration(self, preference=None):
        '''
        Return next iteration bounds
        '''
        if preference:
            self.preference=preference
        self._update_fh()
        
        #tmpzh = list(self.zh)
        self._update_zh(self.zh,self.fh)
        #self.zh = list(np.array(self.zh) / 2. + np.array(self.zh_prev) / 2.)
        #self.zh_prev = tmpzh


        self.fh_lo = list(self.bounds_factory.result(self.zh_prev))

        self.current_iter -= 1

        return self.fh_lo, self.zh
