%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%  The source code of the reference vector guided evolutionary algorithm (RVEA)
%%
%%  See the details of RVEA in the following paper:
%%
%%  R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, 
%%  A Reference Vector Guided Evolutionary Algorithm for Many-objective Optimization,
%%  IEEE Transactions on Evolutionary Computation, 2016
%%
%%  The source code of RVEA is implemented by Ran Cheng 
%%
%%  If you have any questions about the code, please contact: 
%%  
%%  Ran Cheng at ranchengcn@gmail.com
%%  Prof. Yaochu Jin at yaochu.jin@surrey.ac.uk
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function [xPareto, fPareto] = Main(ProbName, SubProblemObjectiveIndices,SubProblemVariablesIndices, NumObj, NumVar, Bounds, lb, ub, FixedIndices, FixedValues, model)
format short;%addpath public;

RunNum = 1;

Problems = {ProbName};

for Prob = 1:length(Problems)
    for Objectives = {NumObj}
        for Run = 1:RunNum
            Algorithm = {'RVEA'};
            Problem = Problems{Prob};
            [xPareto, fPareto] = Start(Algorithm,Problem,cell2mat(Objectives), SubProblemObjectiveIndices, SubProblemVariablesIndices, NumVar, Bounds, lb, ub, FixedIndices, FixedValues, model, Run);
        end;
    end;
end;
end