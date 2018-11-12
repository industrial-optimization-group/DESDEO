function [Generations,N,varargout] = P_settings(Algorithm,Problem,M)
    [Generations,N] = set_problem(Problem,M);
    Parameter = set_algorithm(Algorithm,Problem,M);
    varargout = num2cell(Parameter);
end

function [Generations,N] = set_problem(Problem,M)
%     k = find(~isstrprop(Problem,'digit'),1,'last');
%     D = str2double(Problem(k+1:end));
%     Problem = Problem(1:k);
%     Generations = [1000 500 1000 500];
%     Generations = Generations(D);
    Generations = 1000;
    N = [50 105 120 126 132 112 156 90 275];
    N = N(M-1);
end

function Parameter = set_algorithm(Algorithm,Problem,M)
    Parameter = NaN;
    k = find(~isstrprop(Problem,'digit'),1,'last');
    D = str2double(Problem(k+1:end));
    Problem = Problem(1:k);
    switch Algorithm
        case {'RVEA'}
            p1 = [49 15  7  5  4  3  3  2  3];%changing the number of population
            p2 = [ 0  0  0  0  1  2  2  2  2];
            p1 = p1(M-1);
            p2 = p2(M-1);
            Parameter(1) = p1; Parameter(2) = p2;
        case 'null'
        otherwise
            error([Algorithm,'Not Exist']);
    end
end

