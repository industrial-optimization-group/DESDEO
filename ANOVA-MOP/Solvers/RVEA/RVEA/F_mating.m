%return randomly mathced mating pool
function [MatingPool] = F_mating(Population)
    [N,D] = size(Population);
    MatingPool = zeros(N,D);
    RandList = randperm(N);
    MatingPool = Population(RandList, :);
    if(mod(N,2) == 1)
        MatingPool = [MatingPool; MatingPool(1,:)];
    end;
end
