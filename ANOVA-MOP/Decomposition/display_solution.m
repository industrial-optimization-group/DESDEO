function [na] = display_solution(M,solution)
% Display the decomposition solution
[m n] = size(M);
n_block = size(solution,1)-1;
col_coord = solution{1,2};
n_col_coord = length(col_coord);

seq_row = [horzcat(solution{2:n_block+1,1})];
seq_col = [col_coord horzcat(solution{2:n_block+1,2})];
SolM = M(seq_row,seq_col);

% Coloring the solution matrix
back_color = 0;
block_color = 5;
one_color = 12;

SolM = SolM + back_color;

SolM(:,1:n_col_coord) = SolM(:,1:n_col_coord) + (block_color-back_color);

start_row = 0;
start_col = n_col_coord;
for i = 2:n_block+1
    end_row = start_row + length(solution{i,1});
    end_col = start_col + length(solution{i,2});
    %[end_row end col]
    SolM(start_row+1:end_row,start_col+1:end_col) = SolM(start_row+1:end_row,start_col+1:end_col) + (block_color-back_color);
    start_row = end_row;
    start_col = end_col;
end

for i = 1:m
    for j = 1:n
        if SolM(i,j) > block_color
            SolM(i,j) = one_color;
        end
    end
end

na = SolM;

figure;
clf;
colormap(jet);

SolM = cat(1,SolM,zeros(1,size(SolM,2))+20);
SolM = cat(2,SolM,zeros(1,size(SolM,1))');

SolM = SolM([m:-1:1 m+1],1:n+1);
pcolor(SolM);
axis off

row_position = 0;
col_position = size(M,1)+1.5;
font_size = 10;

for i = 1:m
   text(row_position,i+0.5,num2str(seq_row(i)),'FontSize',font_size);
end
for j = 1:n
   text(j+0.5,col_position,num2str(seq_col(j))','FontSize',font_size);
end