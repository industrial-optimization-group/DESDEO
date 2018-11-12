function [solution] = get_col_solution(M,seq_row,seq_col,pts)
n_block = size(pts,1)+1;
pts = sortrows([[0 0]; pts; size(M)]);
solution = cell(n_block+1,2); %{[row contents] [col contents]}

% Construct the block contents and the coordination contents
coord_m = M(seq_row,seq_col);

for i = 1:n_block
    point0 = pts(i,:);
    point1 = pts(i+1,:);
    solution{i+1,1} = seq_row(point0(1)+1 : point1(1));
    col_contents = seq_col(point0(2)+1 : point1(2));
    
    coord_m(point0(1)+1:point1(1), point0(2)+1:point1(2)) = 0;
    col_coord_index = find(sum(coord_m(:,point0(2)+1:point1(2)),1));
    solution{1,2} = [solution{1,2} col_contents(col_coord_index)];
    
    col_contents(col_coord_index) = [];
    solution{i+1,2} = col_contents;
end