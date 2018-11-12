% Ordinary Tree Visualization
% ---------------------------
%
% Purpose:
% 	The purpose of this algoritm is to plot ordinary tree stucture
%
% Syntax:
%	plot_otm (otm, r)
%	plot_otm (otm, r, orientation)
%	plot_otm (otm, r, orientation, h)
%
% Input:
%	otm - the ordinary tree structure
%	r - the resemblances of the nodes in the tree
%	orientation - orientation of the tree, 0 - vertical (default), 1 - horizontal
%	h - handle to an existing axes where you want to plot the tree (optional)
%
% Last Modified:
%	June 24, 2003
%	rev. March 27, 2004
%
% See Also:
%	rcm2otm
%

function display_tree (otm, r, orientation, h)

if nargin == 2,
	figure ('Name', 'Ordinary Tree');
	clf;
	h = axes;
	%set(h, 'MenuBar', 'none');	
	orientation = 0;	% default: vertical tree
elseif nargin == 3,
	figure ('Name', 'Ordinary Tree');
	clf;
	h = axes;
	%set(h, 'MenuBar', 'none');
end

% Consider a node as shown below, we need to determinate the coordinates of
% x1, x2, x3 and x4.
%
%             2
%             |
%             |
%             |
% 3 ========= 1 ========= 4
% |                       |
% |                       |
%
%

x1 = []; y1 = [];
x2 = []; y2 = [];

leaves = otm2seq(otm);
num_leaves = length(leaves);
num_nodes = max(max(otm));
leaves = [leaves, num_leaves+1:num_nodes];

% coordinates of the leaves
for i = 1:num_leaves,
	x1(leaves(i)) = 5*i-2.5;
	y1(leaves(i)) = r(leaves(i));
	x2(leaves(i)) = 5*i-2.5;
	[a, b] = find(otm(:,num_leaves+1:end) == leaves(i));
	y2(leaves(i)) = r(b+num_leaves);
end

x3 = x1; y3 = y1;
x4 = x1; y4 = y1;

% coorindates of the branches
for i = num_leaves+1:num_nodes,
	tmp = mean(x1(nonzeros(otm(:,i))));
	x1 = [x1, tmp];
	y1 = [y1, r(leaves(i))];
	x2 = [x2, tmp];
	[a, b] = find(otm == i);
	y2 = [y2, r(b)];
%	x3 = [x3, x1(otm(1,i))];
	x3 = [x3, max(x1(nonzeros(otm(:,i))))];
	y3 = y1;
%	x4 = [x4, x1(otm(length(nonzeros(otm(:,i))),i))];
	x4 = [x4, min(x1(nonzeros(otm(:,i))))];
	y4 = y1;
end

% coordinates of the root
tmp =  mean (x2(nonzeros(otm(:,end))));
x1 = [x1, tmp];
y1 = [y1, y2(end)];
x2 = [x2, tmp];
y2 = [y2, 0];

x3 = [x3, max((x2(nonzeros(otm(:,end)))))];
y3 = y1;
x4 = [x4, min((x2(nonzeros(otm(:,end)))))];
y4 = y1;





% Now we can plot the tree

if orientation == 1,	% horizontal tree
	% swap x and y.
	tmp = x1; x1 = y1; y1 = tmp;
	tmp = x2; x2 = y2; y2 = tmp;
	tmp = x3; x3 = y3; y3 = tmp;
	tmp = x4; x4 = y4; y4 = tmp;
end

axes (h);
axis ij;
hold on;



% plot the line
for i=num_leaves+1:num_nodes+1,
	plot([x3(i),x4(i)],[y3(i),y4(i)],'b-','LineWidth',2);
end
for i=1:num_nodes+1,
	plot([x1(i),x2(i)],[y1(i),y2(i)],'g-','LineWidth',2);	
end

% plot the text
seq = otm2seq(otm);
if orientation == 0,
	tick_locations = sort(x1(leaves(1:num_leaves)));
	set(h, 'XTick', tick_locations);
	set(h, 'XTickLabel', seq);
elseif orientation == 1,
	tick_locations = sort(y1(leaves(1:num_leaves)));
	set(h, 'YTick', tick_locations);
	set(h, 'YTickLabel', seq);
	set(h, 'YAxisLocation', 'right');
end


% for i=1:num_leaves,
% 	if orientation == 0,
% 		text (x1(leaves(i))-0.75,1.05,strcat(num2str(seq(i))));
% 	elseif orientation == 1,
% 		text (1.05,y1(leaves(i))-0.75,strcat(num2str(seq(i))));
% 	end
% end

% plot the dots
plot(x1,y1,'ro','Markersize',4,'MarkerEdgeColor','b','MarkerFaceColor','b','LineWidth',1);
%plot(x1,y1,'ro','Markersize',2,'MarkerEdgeColor','b','MarkerFaceColor','b','LineWidth',0.5);



% crap for debug purpose
% plot(x2,y2,'r+','Markersize',6,'MarkerEdgeColor','b','MarkerFaceColor','b','LineWidth',1);	
% plot(x3,y3,'rx','Markersize',6,'MarkerEdgeColor','b','MarkerFaceColor','b','LineWidth',1);	
% plot(x4,y4,'r*','Markersize',6,'MarkerEdgeColor','b','MarkerFaceColor','b','LineWidth',1);		