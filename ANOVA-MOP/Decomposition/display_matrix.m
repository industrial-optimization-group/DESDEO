function [na] = display_matrix(M,seq_row,seq_col)
%Arrange the matrix based on sequences and display it

[m,n] = size(M);
DisplayM = M(seq_row,seq_col);

figure;
clf;
colormap(jet);

DisplayM = cat(1,DisplayM*5+3,zeros(1,size(DisplayM,2))+20);
DisplayM = cat(2,DisplayM,zeros(1,size(DisplayM,1))');

DisplayM = DisplayM([m:-1:1 m+1],1:n+1);
pcolor(DisplayM);
axis off

na = DisplayM;

row_position = 0;
col_position = size(M,1)+1.5;
font_size = 20;

for i = 1:m
   text(row_position,i+0.5,num2str(seq_row(i)),'FontSize',font_size);
end
for j = 1:n
   text(j+0.5,col_position,num2str(seq_col(j))','FontSize',font_size);
end
