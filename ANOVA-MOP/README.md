# ANOVA-MOP_Code
 Copyright (C) 2017 By Mohammad Tabatabaei 

    ANOVAMOP is a free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ANOVAMOP is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details. You should have 
    received a copy of the GNU General Public License
    along with ANOVAMOP.  If not, see <http://www.gnu.org/licenses/>.

 ANOVAMOP: An interactive/non-interactive surrogate-based method for solving 
 high-dimensional computationally expensive #multiobjective optimization 
 problems of the form 
         min {f_1(x),…f_k(x)}    subject to   LB <= x <= UB
 where 
 f_i, i=1,..k, are computationally expensive objective function 
 whose closed-form formulas are not available (i.e., black-box functions). 

 LB and UB are the lower and upper bounds of the decision variables. 
 ANOVAMOP aims at decomposing a high-dimensional problem into a finite number of 
 low-dimensional subproblems. Each subproblem is solved seperately. Solutions of 
 the subproblems are composed to form solutions for the original problem.

 To build surrogate function, in ANOVAMOP, the method developed in 
 
 "M. Tan. Sequential Bayesian polynomial chaos model selection for estimation of
 sensitivity indices. SIAM/ASA Journal on Uncertainty Quantification, 3:146–168,
 2015." is applied. Feel free to replace this method with any another method. 
 
 To apply ANOVAMOP as an interactive method, set "DM=1". In this case, the user 
 provides his/her preferences in a form of a reference point. In this case, 
 the final solutions in the decision and objective spaces are saved in 
 FinalSolutionDecisionSpace and FinalSolutionObjectiveSpace, respectively.
 
 By setting "DM=0", ANOVAMOP is applied as a non-interactive. In this case, a set of
 solutions is provided at the end. The Solutions in the decision and objective spaces of subproblems 
 are saved in SubProblemsDecisionSpacePareto.mat SubProblemsObjectiveSpacePareto.mat, respectively. 
 The composed solutions in the decision and objective spaces for the original problem are saved in 
 DecisionSpaceParetoAll and ObjectiveSpaceParetoAll, respectively.   


 Input:
 The multiobjective optimization problem is defined in “P_objective.m”. 
 P_objective.m is a part of the implementation of RVEA method developed in 

 R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, A Reference Vector Guided 
 Evolutionary Algorithm for Many-objective Optimization, IEEE Transactions
 on Evolutionary Computation, 2016.

 In this implementation of ANOVAMOP, the method developed in 
 
 "L. Chen, Z. Ding, and S. Li. A formal two-phase method for decomposition of
 complex design problems. Journal of Mechanical Design, 127(2):184–195, 2005."
 is applied to decompose the original problem. Feel free to replace this method 
 with any another method.
 
 To solve surrogate problems in the interactive and non-interactive setting, 
 the DIRECT method developed in 

 D. R. Jones, C. D. Perttunen, and B. E. Stuckman. Lipschitzian optimization 
 without the Lipschitz constant. Journal of Optimization Theory and Applications,
 79(1):157-181, 1993.
 
 and
 
 the RVEA method developed in 
 
 "R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, A Reference Vector Guided 
 Evolutionary Algorithm for Many-objective Optimization, IEEE Transactions 
 on Evolutionary Computation, vol. 20, no. 5, pp. 773–791, 2016" 
 
 are incorporated. Feel free to replace these solvers with any other solvers.
 
 

             When using ANOVA-MOP, please cite the following paper:      

 Mohammad Tabatabaei, Alberto Lovisony, Matthias Tan, Markus Hartikainen, 
 and Kaisa Miettinen, ANOVA-MOP: ANOVA Decomposition for Multiobjective 
 Optimization, submitted.
