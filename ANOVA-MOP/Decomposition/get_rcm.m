%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Remarks
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [rcm_row, rcm_col, rcm_rc] = get_rcm(M)
[m,n] = size(M);

for i = 1:m
    rcm_row(i,i) = 1;
    for j = i+1:m
        rcm_row(i,j) = coe_rr(M(i,:),M(j,:));
        rcm_row(j,i) = rcm_row(i,j);
    end
end

for i = 1:n
    rcm_col(i,i) = 1;
    for j = i+1:n
        rcm_col(i,j) = coe_rr(M(:,i),M(:,j));
        rcm_col(j,i) = rcm_col(i,j);
    end
end

for i = 1:m
    for j = 1:n
        %rcm_rc(i,j) = 2*M(i,j)/(sum(M(i,:))+sum(M(:,j)));
        rcm_rc(i,j) = sqrt(M(i,j)/(sum(M(i,:))+sum(M(:,j))-M(i,j)));
    end
end



function r = coe_rr(row_i,row_j)

n_elements = length(row_i);

sum_num = 0;
sum_den = 0;
for i = 1:n_elements
   sum_num = sum_num + min(row_i(i),row_j(i));
   sum_den = sum_den + max(row_i(i),row_j(i));
end
r = sum_num/sum_den;