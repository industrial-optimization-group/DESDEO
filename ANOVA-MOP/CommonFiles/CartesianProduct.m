function [A] = CartesianProduct(S)
%CARTESIAN_PRODUCT Summary of this function goes here
%   Detailed explanation goes here
% Input: a cell array of matrices
% Output: a matric containing all cartecian products of all rows in all
% the matrices
A = S{1};
for i = 2:numel(S)
    A_ = [];
    for k = 1:size(A,1)
        for j = 1:size(S{i},1)
            A_ = [A_;[A(k,:),S{i}(j,:)]];
        end
    end
    A = A_;
end
    
