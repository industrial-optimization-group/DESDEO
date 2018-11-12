function [complexity_value] = get_complexity(M,solution)

[m,n] = size(M);
n_block = size(solution,1)-1;
row_coord = solution{1,1};
col_coord = solution{1,2};

complexity_block = 0;
for i = 1:n_block
    n_row = nnz(sum(M([row_coord solution{i+1,1}],solution{i+1,2}),2));
    n_col = nnz(sum(M(solution{i+1,1},[col_coord solution{i+1,2}]),1));
    complexity_block(i) = n_row*log(2^n_col);
end

row_coord_block = M(row_coord,:);
col_coord_block = M(:,col_coord);

complexity_coord_row = length(row_coord)*log(2^nnz(sum(row_coord_block,1)));
complexity_coord_col = nnz(sum(col_coord_block,2))*log(2^length(col_coord));

complexity_value = (sum(complexity_block)+complexity_coord_row+complexity_coord_col)/(m*log(2^n));
