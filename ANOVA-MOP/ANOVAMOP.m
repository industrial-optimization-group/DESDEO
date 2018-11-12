function ANOVAMOP
%----------------********************************--------------------------
% Copyright (C) 2017 By Mohammad Tabatabaei 
%
% This file is part of the program SURROGATEASF.m
%
%    ANOVAMOP.m is a free software: you can redistribute it and/or modify
%    it under the terms of the GNU General Public License as published by
%    the Free Software Foundation, either version 3 of the License, or
%    (at your option) any later version.
%
%    ANOVAMOP.m is distributed in the hope that it will be useful,
%    but WITHOUT ANY WARRANTY; without even the implied warranty of
%    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%    GNU General Public License for more details.
%
%    You should have received a copy of the GNU General Public License
%    along with ANOVAMOP.m.  If not, see <http://www.gnu.org/licenses/>.
%----------------********************************--------------------------
%
%--------------------------------------------------------------------------
% ANOVAMOP: An interactive/non-interactive surrogate-based method for solving 
% high-dimensional computationally expensive %multiobjective optimization 
% problems of the form 
%         min {f_1(x),…f_k(x)}    subject to   LB <= x <= UB
% where 
% f_i, i=1,..k, are computationally expensive objective function 
% whose closed-form formulas are not available (i.e., black-box functions). 
%
% LB and UB are the lower and upper bounds of the decision variables. 
% ANOVAMOP aims at decomposing a high-dimensional problem into a finite number of 
% low-dimensional subproblems. Each subproblem is solved seperately. Solutions of 
% the subproblems are composed to form solutions for the original problem.

% To build surrogate function, in ANOVAMOP, the method developed in 
% 
% "M. Tan. Sequential Bayesian polynomial chaos model selection for estimation of
% sensitivity indices. SIAM/ASA Journal on Uncertainty Quantification, 3:146–168,
% 2015." is applied. Feel free to replace this method with any another method. 
% 
% To apply ANOVAMOP as an interactive method, set "DM=1". In this case, the user 
% provides his/her preferences in a form of a reference point. In this case, 
% the final solutions in the decision and objective spaces are saved in 
% FinalSolutionDecisionSpace and FinalSolutionObjectiveSpace, respectively.
% 
% By setting "DM=0", ANOVAMOP is applied as a non-interactive. In this case, a set of
% solutions is provided at the end. The Solutions in the decision and objective spaces of subproblems 
% are saved in SubProblemsDecisionSpacePareto.mat SubProblemsObjectiveSpacePareto.mat, respectively. 
% The composed solutions in the decision and objective spaces for the original problem are saved in 
% DecisionSpaceParetoAll and ObjectiveSpaceParetoAll, respectively.   

% Please refer with all questions, comments, bug reports, etc. to
% tabatabaei62@yahoo.com
%----------------********************************--------------------------
%
%
% Input:
% The multiobjective optimization problem is defined in “P_objective.m”. 
% P_objective.m is a part of the implementation of RVEA method developed in 
%
% R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, A Reference Vector Guided 
% Evolutionary Algorithm for Many-objective Optimization, IEEE Transactions
% on Evolutionary Computation, 2016.
%
% In this implementation of ANOVAMOP, the method developed in 
% 
% "L. Chen, Z. Ding, and S. Li. A formal two-phase method for decomposition of
% complex design problems. Journal of Mechanical Design, 127(2):184–195, 2005."
% is applied to decompose the original problem. Feel free to replace this method 
% with any another method.
% 
% To solve surrogate problems in the interactive and non-interactive setting, 
% the DIRECT method developed in 
%
% D. R. Jones, C. D. Perttunen, and B. E. Stuckman. Lipschitzian optimization 
% without the Lipschitz constant. Journal of Optimization Theory and Applications,
% 79(1):157-181, 1993.
% 
% and
% 
% the RVEA method developed in 
% 
% "R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, A Reference Vector Guided 
% Evolutionary Algorithm for Many-objective Optimization, IEEE Transactions 
% on Evolutionary Computation, vol. 20, no. 5, pp. 773–791, 2016" 
% 
% are incorporated. Feel free to replace these solvers with any other solvers.
% 
% 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%             When using ANOVA-MOP, please cite the following paper:      %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Mohammad Tabatabaei, Alberto Lovisony, Matthias Tan, Markus Hartikainen, 
% and Kaisa Miettinen, ANOVA-MOP: ANOVA Decomposition for Multiobjective 
% Optimization, submitted.


clc;
close all;
warning off;
folder = fileparts(which(mfilename)); 
addpath(genpath(folder));
%%Initialization
ProbName='ALBERTO';%Problem's name defined in P_objective.m
d=5;%number of variables
ObjectiveNumber=5;%Number of objective functons
DM=1;%0 means non-interactive setting and 1 means interactive setting
lb=-1*ones(1,d);%lower bounds of variables
ub=1*ones(1,d);%upper bound of variables
NumberSubProblems=2;%Preferred number of subproblems to be obtained by decomposition
VariableIndices=1:d;
save d d;

% Build Surrogates
for objective=1:ObjectiveNumber
    disp(objective)
    SurrogateDataInfo(objective)=SequentialLegendreChaosSensitivityAnalysis(ProbName,objective,ObjectiveNumber,lb,ub,10000);
    TotalSenIndMatrix(objective,:)=SurrogateDataInfo(objective).TotalIndices(:,2)';
end
SurrogateData.SurrogateDataInfo=SurrogateDataInfo;
SurrogateData.TotalSenIndMatrix=TotalSenIndMatrix;
save('SurrogateData','SurrogateData');
TotalSenIndMatrix=SurrogateData.TotalSenIndMatrix;
MaxNumberCommonVariable=d;
MinNumberIndependentVariableInSubProblem=0;
TotalSenIndTemp=TotalSenIndMatrix(:);
TotalSenIndTemp=sort(unique(TotalSenIndTemp));
%Assiging an upperbound for the threshold
TotalSenIndTemp(TotalSenIndTemp>min(max(TotalSenIndMatrix,[],2)))=[];
NumThreshold=length(TotalSenIndTemp);

%Finding all possible decompositions
for i=1:NumThreshold
    Threshold=TotalSenIndTemp(i);
    VarVectorInd=TotalSenIndMatrix>=Threshold;
    TempDecompositionModel=BestDecomposition(VarVectorInd,NumberSubProblems,MinNumberIndependentVariableInSubProblem,MaxNumberCommonVariable);    
    DecompositionModelCandidates(i).Model=TempDecompositionModel;
    DecompositionModelCandidates(i).Threshold=Threshold;
    DecompositionModelCandidates(i).VarVectorInd=VarVectorInd;
    disp([num2str(i) '/' num2str(NumThreshold)])
end
save DecompositionModelCandidates DecompositionModelCandidates;

%Choose the best decomposition
NumCandidateModel=size(DecompositionModelCandidates,2);
BestDecompositionModel=[];
stop=1;
MaxIntVar=0;
while stop    
    for Candidate=1:NumCandidateModel        
        if length(DecompositionModelCandidates(Candidate).Model{1,2}) <=MaxIntVar
            BestDecompositionModel=DecompositionModelCandidates(Candidate);
            BestDecompositionModel.TotalSenIndMatrix=TotalSenIndMatrix;
            stop=0;
            break;            
        end
    end
    if isempty(BestDecompositionModel)
        MaxIntVar=MaxIntVar+1;
    end
end
%%check if interaction column size is zero
if ~isempty(BestDecompositionModel.Model{1,2})
    disp('There are some common variables between subproblems. ANOVA-MOP cannot solve such problems.')
    disp('You may wait for ANOVA-MOPII to solve such problems.')
    return
end

if ~DM% ANOVA-MOP as a non-interactive method    
    VariableBounds=[lb;ub];
    SubProblemObjectiveIndicesTemp=[];
    SubProblemVariablesIndicesTemp=[];
    for SubProbInd=1:NumberSubProblems
        SubProblemObjectiveIndices=BestDecompositionModel.Model{SubProbInd+1,1};
        SubProblemObjectiveIndicesTemp=[SubProblemObjectiveIndicesTemp SubProblemObjectiveIndices];
        SubProblemVariablesIndices=[BestDecompositionModel.Model{1,2} BestDecompositionModel.Model{SubProbInd+1,2}];
        SubProblemVariablesIndicesTemp=[SubProblemVariablesIndicesTemp SubProblemVariablesIndices];
        if length(SubProblemObjectiveIndices)>1 && length(SubProblemVariablesIndices)>1
            FixedIndices=setdiff(VariableIndices,SubProblemVariablesIndices);
            Bounds=VariableBounds(:,SubProblemVariablesIndices);
            FixedValues=mean(VariableBounds(:,FixedIndices));
            [xParetoTemp, fParetoTemp]=SubProblem(SubProblemObjectiveIndices,SubProblemVariablesIndices,Bounds,lb,ub,FixedIndices,FixedValues,SurrogateData.SurrogateDataInfo);
            SubProblemsDecisionSpacePareto{SubProbInd}=xParetoTemp;
            SubProblemsObjectiveSpacePareto{SubProbInd}=fParetoTemp;            
        end
    end
    DecisionSpaceParetoAll=CartesianProduct(SubProblemsDecisionSpacePareto);
    DecisionSpaceParetoAll=[SubProblemVariablesIndicesTemp; ... 
        DecisionSpaceParetoAll];
    DecisionSpaceParetoAll=sortrows(DecisionSpaceParetoAll',1)';
    DecisionSpaceParetoAll(1,:)=[];
    ObjectiveSpaceParetoAll=CartesianProduct(SubProblemsObjectiveSpacePareto);
    ObjectiveSpaceParetoAll=[SubProblemObjectiveIndicesTemp;ObjectiveSpaceParetoAll];
    ObjectiveSpaceParetoAll=sortrows(ObjectiveSpaceParetoAll',1)';
    ObjectiveSpaceParetoAll(1,:)=[];
    save ObjectiveSpaceParetoAll ObjectiveSpaceParetoAll;
    save DecisionSpaceParetoAll DecisionSpaceParetoAll;
    save SubProblemsDecisionSpacePareto SubProblemsDecisionSpacePareto
    save SubProblemsObjectiveSpacePareto SubProblemsObjectiveSpacePareto

else% ANOVAMOP as an interactive method
    FinalSolutionDecisionSpace=zeros(1,d);
    FinalSolutionObjectiveSpace=zeros(1,ObjectiveNumber);
    for SubProbInd=1:NumberSubProblems
        VariableBounds=[lb;ub];
        SubProblemObjectiveIndices=BestDecompositionModel.Model{SubProbInd+1,1};
        SubProblemVariablesIndices=[BestDecompositionModel.Model{1,2} BestDecompositionModel.Model{SubProbInd+1,2}];
        DoInteraction=1;
        clc
        while DoInteraction
            disp(['Indices of objective functions of subproblem #' num2str(SubProbInd) ' are ' num2str(SubProblemObjectiveIndices)'.'])
            disp(['Enter a referenc point as a vector 1x' num2str(length(SubProblemObjectiveIndices)) ' for these objectives'])
            z = input('');
            if (length(z) ~= length(SubProblemObjectiveIndices))
                disp(['The reference point must have a dimension 1x' num2str(length(SubProblemObjectiveIndices)) '.'])
            else
                FixedIndices=setdiff(VariableIndices,SubProblemVariablesIndices);
                FixedValues=mean(VariableBounds(:,FixedIndices));
                VariableBounds(:,FixedIndices)=repmat(FixedValues,2,1);
                [xOptApp, fOptApp]=MakeDecision(z,BestDecompositionModel,SurrogateData,SubProblemObjectiveIndices,VariableBounds);
                disp(['Given reference point = [' num2str(z) '], and '])
                disp(['corresponding prefered solution in the objecive space = [' num2str(fOptApp) '].'])
                Tag=input('Would you like to provide another reference point? Yes = 1 / No = 0 ');
                if Tag == 0
                    DoInteraction=0;
                    FinalSolutionDecisionSpace(SubProblemVariablesIndices)=xOptApp(SubProblemVariablesIndices);
                    FinalSolutionObjectiveSpace(SubProblemObjectiveIndices)=fOptApp;
                end
            end
        end
    end
    clc
    save FinalSolutionDecisionSpace FinalSolutionDecisionSpace
    save FinalSolutionObjectiveSpace FinalSolutionObjectiveSpace
    disp('The final solution in the objective space is')
    disp(['          [' num2str(FinalSolutionObjectiveSpace) ']'])
    disp('The final solution in the decision space is')
    disp(['          [' num2str(FinalSolutionDecisionSpace) ']'])
end

end

function [xOptApp, fOptApp]=MakeDecision(z,DecomposedModel,Surrogate,SubProblemObjectiveIndices,VariableBounds)
opts.es = 1e-4;
opts.maxevals = 500;
opts.maxits = 500;
opts.maxdeep = 1000;
opts.testflag = 0;
opts.showits = 0;
StrucData.Surrogate=Surrogate;
StrucData.DecomposedModel=DecomposedModel;
StrucData.z=z;
StrucData.ObjIndices=SubProblemObjectiveIndices;
StrucData.DecomposedBounds=VariableBounds;
Problem.f ='ASF';
fOptApp=zeros(1,length(SubProblemObjectiveIndices));
[~, xOptApp]=Direct(Problem,VariableBounds',opts,StrucData);
xOptApp=xOptApp';
for Objective=1:length(SubProblemObjectiveIndices) 
    fOptApp(Objective)=SurrogatePrediction(xOptApp,Surrogate.SurrogateDataInfo(SubProblemObjectiveIndices(Objective)));    
end

end

