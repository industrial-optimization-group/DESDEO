function [solution_index,ppp,ppp_info] = Ding_partition_analysis(M,seq_row,seq_col,n_block,min_block,max_coord)

%Start the time
% t0 = clock;

%User input - decomposition criteria
% n_block = 2; %Number of blocks
% min_block = 0; %Minimum number of columns of a block
% max_coord = 4; %Maximum number of columns of the interaction part

%obtain ppp by applying criteria (min_block and max_coord)
[m,n] = size(M);
ppp = [];

for i = 1:m-1
    for j = 1:n-1
        temp_point = [i j];
        temp_sol = get_col_solution(M,seq_row,seq_col,temp_point);
        
        flag = 1;
        for k = 1:size(ppp,1)
            existing_sol = get_col_solution(M,seq_row,seq_col,ppp(k,:));
            if isequal(temp_sol,existing_sol)
                flag = 0;
                break
            end
        end
        
        if check_sol(temp_sol,min_block,max_coord) && flag
            p_index = size(ppp,1)+1;
            ppp(p_index,:) = [i j];
            ppp_info(p_index,:) = [i j length(temp_sol{1,2}) length(temp_sol{2,2}) length(temp_sol{3,2})];
        end
    end
end

%enumeration partitioning analysis
n_ppp = size(ppp,1);

solution_index = [];
new_solution_index = [];

% Set up the one-point solution
for i = 1:n_ppp
    temp_sol = get_col_solution(M,seq_row,seq_col,ppp(i,:));
    
    %check temp_sol
    if check_sol(temp_sol,min_block,max_coord)
        solution_index(size(solution_index,1)+1,:) = i;
    end
end

while size(solution_index,2) < n_block-1
    for i = 1:size(solution_index,1)
        for j = 1:n_ppp
            %a = find(solution_index(i,:) == j)
            
            %if isempty(find(solution_index(i,:) == j)) %new point to the existing solution
            if j > solution_index(i,:)
                temp_sol_index = [solution_index(i,:) j];
                temp_sol_pts = ppp(temp_sol_index,:);
                temp_sol = get_col_solution(M,seq_row,seq_col,temp_sol_pts);
                
                %check temp_sol
                if sort(temp_sol_pts) == sortrows(temp_sol_pts) %check relative positions of partition points
                    if check_sol(temp_sol,min_block,max_coord) %check decomposition criteria
                        new_solution_index(size(new_solution_index,1)+1,:) = temp_sol_index;
                    end
                end
            end
        end
    end
    solution_index = new_solution_index;
    new_solution_index = [];
    %return
end
% etime(clock,t0)


function [check] = check_sol(solution,min_block,max_coord)
n_block = size(solution,1)-1;
check = 1;

if size(solution{1,2},2) > max_coord
    check = 0;
    return
end

for i = 1:n_block
    if size(solution{i+1,2},2) < min_block
        check = 0;
        return
    end
end
