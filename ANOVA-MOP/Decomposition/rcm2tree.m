% Ordinary Tree Construction
% --------------------------
%
% Purpose:
% 	The purpose of this algoritm is to construct an ordinary tree based on a resemblance 
% 	coefficient matrix
%
% Syntax:
%	[otm, r] = rcm2tree (rcm)
%
% Input:
%	rcm - the resemblance coefficient matrix
%
% Output:
%	otm - a matrix showing the ordinary tree structure
%	r - the resemblances of the nodes in the ordinary tree
%
% Last Modified:
%	June 24, 2003
%
% See Also:
%	calculate_rcm
%


function [otm, r] = rcm2tree (rcm)

	[m, n] = size(rcm);
	
	% rcm_owner:	denotes which branch the leaf/branch is under
	% 		orignally the owner is the leafs themselves
	rcm_owner = [1:n]';		
					
	% otm_r:	denotes the value at which leafs are combined										
	% otm_nodes:	stores a list of leafs that the branch contains
	% i_otm: index to otm_r and otm_nodes -> index to leafs / branches
	
	i_otm = n;				
%	otm_r = zeros (1, 2*n);		
	otm_r = ones (1, 2*n);		
	otm_nodes = zeros (2*n);	
	otm_nodes(1,1:n) = 1:n;

	otm_size = zeros (1,2*n);	
	otm_size(1:n) = 1;
	
	rcm = rcm - eye (n, n);		% remove the diagonal elements from rcm

	nodecount = n;
		
	i_rcm_2 = 1:n;
	while length (i_rcm_2) > 0,

		i_otm = i_otm + 1;		
		
		% find the index(es) to the largest rcm element(s)
		otm_r(i_otm) = max(max(rcm));
%		[a, b] = find ((rcm + 0.1) >= otm_r(i_otm));
		[a, b] = find (rcm == otm_r(i_otm));
		
		% %%%%
		n = length(a);
		i_temp = [a(1), b(1)];
		for i = 2:n,
			if isempty (intersect (i_temp, a(i))) | isempty (intersect (i_temp, a(i))),
				% do nothing
			else
				i_temp = [i_temp, a(i), b(i)];
			end
		end		
		%i_rcm_1 = unique ([a; b]);
		i_rcm_1 = unique (i_temp);
		index = rcm_owner (i_rcm_1);
		
		% average the rcm element
		index_not = setdiff(rcm_owner, index);
		i_rcm_2 = setdiff(1:length(rcm), i_rcm_1);
		
		%rcm_tmp = mean (rcm(i_rcm_2,i_rcm_1)');
		rcm_tmp = mean (rcm(i_rcm_2,i_rcm_1)');

		rcm = rcm(i_rcm_2,i_rcm_2);
		rcm = [rcm,rcm_tmp';rcm_tmp,0];
	
		% name/index the new branch
		rcm_owner = [rcm_owner(i_rcm_2); i_otm];

		% store the index of the elements to be combined 
		otm_nodes(1:length(index),i_otm) = index;
		
		nodecount = nodecount + 1;
	end
	
	% output
	otm = otm_nodes(:,1:nodecount);
	r = otm_r(:,1:nodecount);
	
	%otm = sparse(otm);