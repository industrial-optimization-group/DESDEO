%%%%%%%%%%%%%%%%%%%%%%%%%
% Update: June 10, 2010
% Purpose: generate the decomposition based on Ding's algorithms
%%%%%%%%%%%%%%%%%%%%%%%%%

function [seq_row,seq_col] = Ding_dependency_analysis(M)

[rcm_row, rcm_col] = get_rcm(M);
rcm_row(isnan(rcm_row))=0;%By me
rcm_col(isnan(rcm_col))=0;%By me
tree_row = rcm2tree(rcm_row);
tree_col = rcm2tree(rcm_col);

tree_row = node_associate(tree_row,M',rcm_row);
tree_col = node_associate(tree_col,M,rcm_col);

tree_row = branch_associate(tree_row,M');
tree_col = branch_associate(tree_col,M);

[tree_row, tree_col] =  tree_associate(tree_row, tree_col, M);

seq_row = tree2seq(tree_row);
seq_col = tree2seq(tree_col);

[seq_row, seq_col] = matrix_arrangement(M,seq_row,seq_col);




%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Node Association
% ----------------
%
% Purpose: 
% 	The purpose of node association algorithm is to manage the dependencies among the sub-nodes 
% 	of a node, which is not considered in the tree creation algorithm.  In branches with more 
% 	than two sub-nodes, and the node association algorithm is applied to order these sub-nodes 
% 	into a sequence based on their dependencies.
%
% Description:
% 	The heuristics behind this algorithm is to put the sub-nodes that have most dependencies 
% 	with other sub-nodes in the center of the sequence while the other sub-nodes are put to the 
% 	both ends of the sequence.  
%
% Syntax:
%	[otm] = node_associate (otm, iM)
%
% Input:
% 	otm 	- Ordinary Tree 
%	iM	- Incidence Matrix
%
% Output:
%	otm - The modified Ordinary Tree
%
% Last Modified:
%	June 24, 2003
%

function [otm] = node_associate (otm, iM, rcm)

	seq = tree2seq(otm);
    rcm = rcm(seq,seq); % rcm of the arranged incidence matrix
	leaves = otm2leaves(otm);	% express the tree structure in terms of leaf indices instead of node indices
	[x, nn] = size(otm);		% find the number of nodes - nn
	
	for j=1:nn,
		num_nodes = length(nonzeros(otm(:,j)));		% number of subnode within the node
		if  num_nodes > 2,	% every nodes except the leaves

			% calculate the dependencies between the nodes by adding up the values 
			% of their subnodes
			num_ones = [];
			for i=1:num_nodes,
				node = otm(i,j);
				leaf = nonzeros(leaves(:,node));
				tmp = sum(sum(rcm(:,leaf)));
				num_ones = [num_ones, tmp];				
			end			
			
			% sort them in accending order
			n = num_nodes;
			[y, index_2] = sort (num_ones);

			% put the accending order in a special form, where the largest values 
			% are in the center, and the smaller ones are on the side
			index_3 = zeros (1, n);
						
			a = 1;
			b = n;	
			i = 1;
			while 1,
				index_3 (a) = index_2 (i);
				a = a + 1;
				i = i + 1;
				if i > n,
					break;
				end
				index_3 (b) = index_2 (i);
				b = b - 1;
				i = i + 1;
				if i > n,
					break;
				end		
			end
			
			% update the node in the tree structure
			tmp = otm(:,j);
			otm(1:n,j) = tmp(index_3);
		end
    end


    
% Branch Association
% ------------------
%
% Purpose: 
% 	The purpose of this algorithm is to perform branch association. 
%
% Syntax:
%	[otm] = branch_associate (otm, iM)
%
% Input:
% 	otm 	- Ordinary Tree 
%	iM	- Incidence Matrix
%
% Output:
%	otm - The modified Ordinary Tree
%
% Last Modified:
%	June 24, 2003
%	March 24, 2003
%


function [otm] = branch_associate (otm, iM)

	[a,b] = size (iM);
	[m,n] = size (otm);
		
	% generate a matrix that contains the leafs of each branch
	otm_leafs = otm2leaves (otm);
	
	% branch association
	for i = n:-1:a+2,
		num_nodes = nnz(otm(:,i));						
		for j = 1:num_nodes-1,
			% pick a node as reference
			ref_node = otm(j,i);
			leavesA = nonzeros(otm_leafs(:,ref_node));
			cmp_node = otm(j+1,i);
			leavesB = nonzeros(otm(:,cmp_node));
%			leavesB = nonzeros(otm_leafs(:,cmp_node));
			
			% sort leavesB with respect to ref_node
			rb = [];
			[num_leaves, zzz] = size(leavesB);
			for k = 1:num_leaves,
				
				leavesC = nonzeros(otm_leafs(:,leavesB(k)));
				if isempty (leavesC) | isempty (leavesA),
					rb = [];
				else				
					% leavesC is the children of leavesB
					% leavesA is the children of the ref_node
		 			tmp = (sum(sum(iM(:,leavesA))) + sum(sum(iM(:,leavesC)))) ./ prod(size(leavesA)) ./ prod(size(leavesC));
	 				rb = [rb, tmp];
				end
				
			end
% 	 		[y, index] = sort (-rb);
 	 		[y, index] = reverse (rb);

 	 		new_nodes = otm(index,cmp_node);
 	 		otm(1:length(new_nodes),cmp_node) = new_nodes;	

			
		end
	end

function [y, index] = reverse (input),
	len = length (input);
	if input(1) < input (end),
		% flip the sequence
		index = len:-1:1;		
		y = input(index);
	else
		% keep the sequence
		index = 1:len;		
		y = input;
    end
    
    
    
    
    
    
% Tree Association
% ----------------
%
% Purpose: 
% 	The purpose of this algorithm is to ensure that the "1" elements in a diagonal matrix 
% 	is along the main diagonal.
%
% Description: 
%	See Chapter 3.5
%
% Syntax:
%	[otm_row_new, otm_col_new] =  tree_associate (otm_row, otm_col, iM)
%
% Input:
% 	otm_row - Ordinary Tree (Row) 
%	otm_col - Ordinary Tree (Column)
%	iM	- Incidence Matrix
%
% Output:
%	otm_row_new - The modified Ordinary Tree (Row)
%	otm_col_new - The modified Ordinary Tree (Column)
% 
% Last Modified:
%	March 24, 2004
%

function [otm_row_new, otm_col_new] =  tree_associate (otm_row, otm_col, iM),

	% Arrange the incidence matrix in the order given by the row and column trees.
	seq_row = tree2seq (otm_row);
	seq_col = tree2seq (otm_col);
	mat = iM(seq_row, seq_col);
	
	% Let G1 be the G value of the arranged matrix using equation (4)
	G1 = calculate_Gvalue (mat);
	
	% Let TB be the column tree
	current_tree = 'Column';
	M = mat (seq_row,:);
	TB = otm_col;
	
	while 1,
		
		% Let ND be the root node of TB
		ND = size (TB, 2);
		
		% the recursive loop thing
		TB = arrange_branch (M, TB, ND);
		
		if strcmp(current_tree, 'Column'),

			% Arrange the matrix based on the tree			
			seq_row = tree2seq (otm_row);
			seq_col = tree2seq (TB);
			mat_new = iM(seq_row, seq_col);

			% Let G2 be the G-value of the arranged matrix			
			G2 = calculate_Gvalue (mat_new);

			% save results if there is improvement in G value
			if G1 > G2,	
				G1 = G2;
				otm_col = TB;
			end
			
			% Let TB be the row tree
			current_tree = 'Row';
			M = iM';
			M = M(seq_col,:);
			TB = otm_row;
			
		else % row tree
			
			% Arrange the matrix based on the tree
			seq_row = tree2seq(TB);
			seq_col = tree2seq(otm_col);
			mat_new = iM(seq_row, seq_col);
			
			% Let G2 be the G-value of the arranged matrix
			G2 = calculate_Gvalue((mat_new));

			% save results if there is improvement in G value			
			if G1 > G2,
				G1 = G2;
				otm_row = TB;
			else
				break;
			end			
			
			% Let TB be the column tree
			current_tree = 'Column';
			M = iM(seq_row,:);
			TB = otm_col;
			
		end
		
	end	% while

	% output
 	otm_row_new = otm_row;
 	otm_col_new = otm_col;

% --------------------------------------------------------------------------------------	

function TB = arrange_branch (M, TB, ND),	
	
	% Let B be the branches of ND
	B = nonzeros ( TB (:,ND) );	

	% For each branch in B, calculate a value D using equation (12)
	D = [];
	for i = 1:length(B),
		seq = nonzeros ( tree2seq (TB, B(i)) );
		[X, i] = find(M(:,seq));
		D = [D, mean(X)];
	end
	
	% Sort the branches in B in ascending order based on their D values
	[D_sorted, i_sorted] = sort(D);
	B = B(i_sorted);
	
	% Arrange the branches of node ND based on the branch order in B
	TB (1:length(B),ND) = B;
		
	% Push all the non-leafs branches in B into stack ST
	NL = size(M,2); % number of leaves in the OTM
	ST = B(find(B > NL));
	
	% ST is empty?
	if isempty (ST),
		% return
	else
		% Pop out one branch into TB
		for i = 1:length(ST),
			TB = arrange_branch (M, TB, ST(i));
		end
    end

    
 % Matrix Arrangement
% ------------------
%
% Purpose:
% 	The purpose of the matrix arrangement algorithm is to refine the matrix obtained from 
% 	the binary tree association by sequencing columns and rows such that the ls elements 
% 	can be located along the main diagonal as compact as possible.  
%
%
% Syntax:
%	[i_MR, i_MC] = matrix_arrange (iM)
%
% Input:
%	iM - The matirx to be arranged
%
% Output:
%	i_MR - the index to the new order of the row elements
%	i_MC - the index to the new order of the column elmenets
%
% Last Modified:
%	June 24, 2003
%

%function [i_MR, i_MC] = matrix_arrange (iM)
% 	
% function [i_MC, i_MR] = matrix_arrange (seqC, seqR, iM)
% 	iM = iM(seqR,seqC);
% 	
% 	
% 	[m, n] = size(iM);
% 	j = ((1:n)'*ones(1,m))';
% 	i = (1:m)'*ones(1,n);
% 
% 	i_MR = 1:m;
% 	i_MC = 1:n;
% 	G = inf;	
% 	
% 	i_MR_old = 1:m;
% 	i_MC_old = 1:n;
% 	G_old = inf;
% 
% 	max_iteration = 1500;
% 	iteration = 0;
% 
% 	while (1),
% 		% calculate the mean index values (row).
% 		mean_row = (j.*iM(i_MR,i_MC));			%uri
% 	 	mean_row = sum(mean_row') ./ sum(iM(i_MR,i_MC)');
% 		i_MR_old = i_MR;
% 		% sort the values in ascending order.
% 		[y, i_MR] = sort (mean_row');			
% 		% make sure the sorted order results in a better G-value.		
% 		G_old = G;
% 		G = calculate_Gvalue (iM(i_MR,i_MC));
%   		if G > G_old,
%   			i_MR = i_MR_old;
%     			break;			
% 		end
% 
% 		% calculate the mean index values (column)
% 		mean_col = (i.*iM(i_MR,i_MC));			%urj
% 		mean_col = sum(mean_col) ./ sum(iM(i_MR,i_MC));		
% 		i_MC_old = i_MC;		
% 		% sort the values in ascending order.		
% 		[y, i_MC] = sort (mean_col);
% 		% make sure the sorted order results in a better G-value.		
% 		G_old = G;
% 		G = calculate_Gvalue (iM(i_MR,i_MC));
%   		if G > G_old,
%   			i_MC = i_MC_old;
%   			break;						
% 		end
% 
% 		% time constraint for calculation - maximum number of iteration
% 		iteration = iteration + 1;		
% 		if iteration > max_iteration, 
% 			break;
% 		end			
% 	end	


% ========================
% Ding's algorithm
% ========================

% %Refine the matrix
function [Sequn2,Sequn1]=matrix_arrangement(MatrixAC1,Sequn2,Sequn1)
SM=size(MatrixAC1);
STDs1=ones(1,SM(1));
STDs2=ones(2,SM(2));
MatrixAC=MatrixAC1(Sequn2,Sequn1);
Sstd=0;
for k=1:SM(1)
   a=find(MatrixAC(k,:));
   b=std(a,1);
   b(isnan(b))=0;
   STDs1(k)=b;
   Sstd=Sstd+b;
end
for k=1:SM(2)
   a=find(MatrixAC(:,k));
   b=std(a,1);
   b(isnan(b))=0;
   STDs2(k)=b;
   Sstd=Sstd+b;
end
Sequn3=Sequn1;
Sequn4=Sequn2;
g=Sstd;

FG2=0;
FG1=1;
%f=0;
FG=1;
while FG==1
   MatrixAC=MatrixAC1(Sequn2,Sequn1);
   %a=size(MatrixAC,2);
   b=[];
   %d=0;
   for k=1:SM(2)
      c=MatrixAC(:,k);
      c=find(c);
      if isempty(c)
          c=0;
      end
      %b=[b mean(c)+max(c)-min(c)];
      b=[b mean(c)];
      %d=d+std(c,1);
   end
   %d33=d;
   [e, h]=sort(b);
   Sequn1=Sequn1(h);
   MatrixAC=MatrixAC1(Sequn2,Sequn1);
   
   Sstd=0;
   for k=1:SM(1)
       stdTemp=std(find(MatrixAC(k,:)),1);
       stdTemp(isnan(stdTemp))=0;
       Sstd=Sstd+stdTemp;
   end
   for k=1:SM(2)
       stdTemp=std(find(MatrixAC(:,k)),1);
       stdTemp(isnan(stdTemp))=0;
       Sstd=Sstd+stdTemp;
   end
   d=Sstd;
   if d>g
      Sequn1=Sequn3;
      Sequn2=Sequn4;
      MatrixAC=MatrixAC1(Sequn2,Sequn1);
      if FG2==1
         break;
      end
      FG2=1;
   elseif d==g
      if FG2==1


         break;
      end
      FG2=1;

   else
      g=d;
      Sequn3=Sequn1;
      Sequn4=Sequn2;
      FG2=0;
   end
   
   MatrixAC=MatrixAC';
   %a=size(MatrixAC,2);
   b=[];
   for k=1:SM(1)
      c=MatrixAC(:,k);
      c=find(c);
      if isempty(c)
          c=0;
      end
      %b=[b mean(c)+max(c)-min(c)];
      b=[b mean(c)];
      %d=d+std(c,1);
   end
   %d44=d-d33;
   [e, h]=sort(b);

   Sequn2=Sequn2(h);
   MatrixAC=MatrixAC1(Sequn2,Sequn1);
   Sstd=0;
   for k=1:SM(1)
       stdTemp=std(find(MatrixAC(k,:)),1);
       stdTemp(isnan(stdTemp))=0;
       Sstd=Sstd+stdTemp;
   end
   for k=1:SM(2)
       stdTemp=std(find(MatrixAC(:,k)),1);
       stdTemp(isnan(stdTemp))=0;
       Sstd=Sstd+stdTemp;
   end
   d=Sstd;
   
   %d=d+std(c,1);
   %if f==0
   %   f=1;
   %   g=d;
   %   Sequn3=Sequn1;
   %   Sequn4=Sequn2;
   %else
   if d>g
      Sequn1=Sequn3;
      Sequn2=Sequn4;
      if FG2==1
         break;
      end
      FG2=1;
   elseif d==g
      if FG2==1
         break;
      end
      FG2=1;
   else
      g=d;
      Sequn3=Sequn1;
      Sequn4=Sequn2;
      FG2=0;
   end
   %end
end
%[Sequn1,Sequn2]=MatrRefine(Sequn1,Sequn2,MatrixAC);

% G-value Calculation
% -------------------
% 
% Purpose:
% 	The purpose of this algorithm is to determine the G-value of a matrix
% 
% Syntax:
% 	[G] = calculate_Gvalue (iM)
% 
% Input:
% 	iM - The incidence matirx (m x n) for the G-value
% 
% Output:
% 	G - the G-value for the incidence matrix
% 
% Last Modified:
% 	March 24, 2004
% 

function G = calculate_Gvalue (iM),
	
	sum_std = 0;	% sum of standard deviation
	[numR, numC] = size(iM);
	
	for k = 1:numR,
		tmp = find(iM(k,:));
		sum_std = sum_std + std(tmp);
	end
	
	for k = 1:numC,
		tmp = find(iM(:,k));
		sum_std = sum_std + std(tmp);
	end
	
	G = sum_std;
    
% otm2leaves
% ----------
%
% Purpose:
% 	The purpose of this algorithm is to express the indecies of nodes in an ordinary tree 
% 	structure in terms of their leaves indices.
% 
% Syntax:
% 	[otm_leafs] = otm2leaves (otm)
% 
% Input:
% 	otm - the ordinary tree structure
% 
% Output:
% 	otm_leafs - the orindary tree structure expressed in terms of leaves indecies
%
% Last Modified:
%	June 24, 2003
%
% See Also:
%	rcm2otm
%	
%

function [otm_leafs] = otm2leaves (otm)

	[m,n] = size (otm);
	tmp = sum (otm == 0);
	a = max (find ( tmp == max(tmp) ));
	
	% generate a matrix that contains the leafs of each branch
	otm_leafs = zeros (n);
	otm_leafs (1,1:a) = 1:a;
	for i = a+1:n,
		num_nodes = nnz(otm(:,i));		
		tmp = [];
		for j = 1:num_nodes,
			tmp = [tmp; nonzeros(otm_leafs(:,otm(j,i)))];
			[x, y] = size (tmp);
			otm_leafs (1:x,i) = tmp;
		end
	end