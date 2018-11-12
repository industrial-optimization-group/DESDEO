function BestDecompositionModel=BestDecomposition(M,NumberSubProblems,MinNumberIndependentVariableInSubProblem,MaxNumberCommonVariable)

[seq_row,seq_col] = Ding_dependency_analysis(M);
[solution_index,ppp,ppp_info] = Ding_partition_analysis(M,seq_row,seq_col,NumberSubProblems,MinNumberIndependentVariableInSubProblem,MaxNumberCommonVariable);
NumberSolution=size(solution_index,1);
ComplexityArray=zeros(1,NumberSolution);
for sol=1:NumberSolution
    Solution(sol).Data=get_col_solution(M,seq_row,seq_col,ppp(solution_index(sol,:),:));
    ComplexityArray(sol)=get_complexity(M,Solution(sol).Data);
end
ComplexityArray=round(ComplexityArray*1000)/1000;
CandidateIndices=find(ComplexityArray==min(ComplexityArray));
NumberCandidate=length(CandidateIndices);

if NumberCandidate==1
    BestDecompositionModel=Solution(CandidateIndices).Data;
else
    BestDecompositionModel=Solution(1).Data;
end

for Candidate=2:NumberCandidate
    CandidateIndix=CandidateIndices(Candidate);
    CandidateSolution=Solution(CandidateIndix).Data;
    for SubProblem=1:NumberSubProblems
        NumObjSolution(SubProblem)=size(CandidateSolution{SubProblem+1,1},2);
        NumObjBest(SubProblem)=size(BestDecompositionModel{SubProblem+1,1},2);
        NumVarSolution(SubProblem)=size(CandidateSolution{SubProblem+1,2},2);
        NumVarBest(SubProblem)=size(BestDecompositionModel{SubProblem+1,2},2);
    end
    if (std(NumObjSolution,1)<std(NumObjBest,1)) || (std(NumVarSolution,1)<std(NumVarBest,1)) || size(CandidateSolution{1,2},2)<size(BestDecompositionModel{1,2},2)
        BestDecompositionModel=CandidateSolution;
    end
    
end
BestDecompositionModel{1,2}=sort(BestDecompositionModel{1,2});
for SubProblem=1:NumberSubProblems
    BestDecompositionModel{SubProblem+1,1}=sort(BestDecompositionModel{SubProblem+1,1});
    BestDecompositionModel{SubProblem+1,2}=sort(BestDecompositionModel{SubProblem+1,2});
end
