% Leaves Sequence Generation
% --------------------------
%
% Purpose:
% 	The purpose of this algoritm is to generate the sequences for the 
% 	elements in a matrix based on its ordinary tree structure
% 
% Description:
% 	Consider the following ordinary tree structure, otm:
% 
%              root
%               |
%             ++++++
%             |    |
%           ++++ +++++
%           |  | | | |
%          +++ | | | |
%          | | | | | |
%          5 4 1 2 3 6
% 
% 	Applying this function will result in the sequence: [5, 4, 1, 2, 3, 6]
% 
% Syntax:
% 	[sequence] = otm2seq (otm)
% 
% Input:
% 	otm - the ordinary tree structure
% 	root - the index of which the sequence is to be generated (optional)
% 
% Output:
% 	sequence - the indices to the elements
%
% Last Modified:
%	June 24, 2003
%
% See Also:
%	rcm2otm
%


function [sequence] = tree2seq (otm, root)

	[m, n] = size(otm);	
	sequence = [];
	
	if nargin == 0,
		error ('Invalid inputs');
	elseif nargin == 1,

		% check each coloum in the otm matrix in order to find the root node
		% it scans the matrix from the last column to the first and locate the first column with non-zero elements

		for i = n:-1:1,
			nz = nonzeros(otm(:,i));
			if ~isempty (nz)
				[num_nodes, x] = size (nz);
				for j = 1:num_nodes,
					sequence = tree2seq(otm, i);
				end
				break								
			end
		end
	elseif nargin == 2,

		% recursively generate the sequence
		
		nodes = nonzeros(otm(:,root));
		[num_nodes, x] = size (nodes);
		for j = 1:num_nodes,
			if nodes(j) == otm(1,nodes(j)),
				% a leaf is reached
				sequence = [sequence, nodes(j)];
			else
				% not a leaf
				% thus, recursively determine the sequence within the node
				sequence = [sequence, tree2seq(otm, nodes(j))];
			end
		end
	end
	