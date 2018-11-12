function [FrontValue,MaxFront] = P_sort(FunctionValue,operation)

% Efficient non-dominated sort on sequential search strategy, TEVC, 2014,
% Xingyi Zhang, Ye Tian, Ran Cheng and Yaochu Jin
% Copyright 2014 BCMA Group, Written by Mr Ye Tian and Prof Xingyi Zhang
% Contact: xyzhanghust@gmail.com

    if nargin<2
        kinds=1;
    elseif strcmp(operation,'half')
        kinds=2;
    elseif strcmp(operation,'first')
        kinds=3;
    else
        kinds=1;
    end
    
    [N,M] = size(FunctionValue);
    MaxFront = 0;
    Sorted = false(1,N);
    [FunctionValue,rank] = sortrows(FunctionValue);
    FrontValue = zeros(1,N) + inf;
    while (kinds==1 && sum(Sorted)<N) || (kinds==2 && sum(Sorted)<N/2) || (kinds==3 && MaxFront<1)
        MaxFront = MaxFront + 1;
        ThisFront = false(1,N);
        for i = 1 : N
            if ~Sorted(i)
                x = 0;
                for j = 1 : N
                    if ThisFront(j)
                        x = 2;
                        for j2 = 2 : M
                            if FunctionValue(i,j2) < FunctionValue(j,j2)
                                x = 0;
                                break;
                            end
                        end
                        if x == 2
                            break;
                        end
                    end
                end
                if x ~= 2
                    ThisFront(i) = true;
                    Sorted(i) = true;
                end
            end
        end
        FrontValue(rank(ThisFront)) = MaxFront;
    end
end