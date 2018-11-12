function [x, f]=SubProblem(SubProblemObjectiveIndices,SubProblemVariablesIndices,Bounds,lb,ub,FixedIndices,FixedValues,model)
NumObj=length(SubProblemObjectiveIndices);
NumVar = length(SubProblemVariablesIndices);
[x, f]=Main('Surrogate', SubProblemObjectiveIndices,SubProblemVariablesIndices, NumObj, NumVar, Bounds, lb, ub, FixedIndices, FixedValues, model);
end

function [y, cons] = SubProblem_objFun(x0,SubProblemObjectiveIndices,SubProblemVariablesIndices,FixedIndices,FixedValues,VariableBounds,model)
% % x=x0;
numPop=size(x0,1);
range=VariableBounds(2,:)-VariableBounds(1,:);
range(:,FixedIndices)=[];
x0=((x0+1).*repmat(range,numPop,1))/2+repmat(VariableBounds(1,SubProblemVariablesIndices),numPop,1);
numVar=length(SubProblemVariablesIndices);%+length(FixedIndices);
x=zeros(numPop,numVar);
x(:,SubProblemVariablesIndices)=x0;
x(:,FixedIndices)=FixedValues;
numObj=length(SubProblemObjectiveIndices);
y = zeros(1,numObj);
cons = [];
for objective=1:numObj
    y(objective)=SurrogatePrediction(x,model(SubProblemObjectiveIndices(objective)));
%     fOrg=DTLZ5_12(x,eps);
%     if abs(y(objective)-fOrg(SubProblemObjectiveIndices(objective)))>10^-3
%         [objective y(objective) fOrg(objective)]
%     end
end
end




