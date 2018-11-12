%This file includes the original and scaled DTLZ1 to DTLZ4

function [Output,Boundary,Coding] = P_objective(Operation,Problem,M,Input)
k = find(~isstrprop(Problem,'digit'),1,'last');
    switch Problem(1:k)
        case 'DTLZ'
            [Output,Boundary,Coding] = P_DTLZ(Operation,Problem,M,Input);
        case 'SDTLZ'
            [Output,Boundary,Coding] = P_SDTLZ(Operation,Problem,M,Input);
        otherwise
            error([Problem,'Not Exist']);
    end
end

function [Output,Boundary,Coding] = P_DTLZ(Operation,Problem,M,Input)
    persistent K;
    Boundary = NaN; Coding = NaN;
    switch Operation
        %Population Initialization
        case 'init'
            k = find(~isstrprop(Problem,'digit'),1,'last');
            K = [5 10 10 10 10 10 20];
            K = K(str2double(Problem(k+1:end)));
            
            D = M+K-1;
            MaxValue   = ones(1,D);
            MinValue   = zeros(1,D);
            Population = rand(Input,D);
            Population = Population.*repmat(MaxValue,Input,1)+(1-Population).*repmat(MinValue,Input,1);
            
            Output   = Population;
            Boundary = [MaxValue;MinValue];
            Coding   = 'Real';
        %Objective Function Evaluation
        case 'value'
            Population    = Input;
            FunctionValue = zeros(size(Population,1),M);
            switch Problem
                case 'DTLZ1'
                    g = 100*(K+sum((Population(:,M:end)-0.5).^2-cos(20.*pi.*(Population(:,M:end)-0.5)),2));
                    for i = 1 : M
                        FunctionValue(:,i) = 0.5.*prod(Population(:,1:M-i),2).*(1+g);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*(1-Population(:,M-i+1));
                        end
                    end
                case 'DTLZ2'
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'DTLZ3'
                    g = 100*(K+sum((Population(:,M:end)-0.5).^2-cos(20.*pi.*(Population(:,M:end)-0.5)),2));
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'DTLZ4'
                    Population(:,1:M-1) = Population(:,1:M-1).^100;
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
            end
            Output = FunctionValue;
        %Sample True PFs
        case 'true'
            switch Problem
                case 'DTLZ1'
                    Population = T_uniform(Input,M);
                    Population = Population/2;
                case {'DTLZ2','DTLZ3','DTLZ4'}
                    Population = T_uniform(Input,M);
                    for i = 1 : size(Population,1)
                    	Population(i,:) = Population(i,:)./norm(Population(i,:));
                    end
            end
            Output = Population;
    end
end


function [Output,Boundary,Coding] = P_SDTLZ(Operation,Problem,M,Input)
    persistent K;
    persistent F;
    Boundary = NaN; Coding = NaN;
    switch Operation
        %Population Initialization
        case 'init'
            k = find(~isstrprop(Problem,'digit'),1,'last');
            K = [5 10 10 10 10 10 20];
            K = K(str2double(Problem(k+1:end)));
            F = [10 10 10 10 10 5 4 3 2 2];
            F = F(M);
            
            D = M+K-1;
            MaxValue   = ones(1,D);
            MinValue   = zeros(1,D);
            Population = rand(Input,D);
            Population = Population.*repmat(MaxValue,Input,1)+(1-Population).*repmat(MinValue,Input,1);
            
            Output   = Population;
            Boundary = [MaxValue;MinValue];
            Coding   = 'Real';
        %Objective Function Evaluation
        case 'value'
            Population    = Input;
            FunctionValue = zeros(size(Population,1),M);
            switch Problem
                case 'SDTLZ1'
                    g = 100*(K+sum((Population(:,M:end)-0.5).^2-cos(20.*pi.*(Population(:,M:end)-0.5)),2));
                    for i = 1 : M
                        FunctionValue(:,i) = 0.5.*prod(Population(:,1:M-i),2).*(1+g);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*(1-Population(:,M-i+1));
                        end
                    end
                case 'SDTLZ2'
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'SDTLZ3'
                    g = 100*(K+sum((Population(:,M:end)-0.5).^2-cos(20.*pi.*(Population(:,M:end)-0.5)),2));
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'SDTLZ4'
                    Population(:,1:M-1) = Population(:,1:M-1).^100;
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
            end
            Output = FunctionValue.*repmat((F.^(0:M - 1)), [size(FunctionValue,1) 1]);
        %Sample True PFs
        case 'true'
            switch Problem
                case 'SDTLZ1'
                    Population = T_uniform(Input,M);
                    Population = Population/2;
                case {'SDTLZ2','SDTLZ3','SDTLZ4'}
                    Population = T_uniform(Input,M);
                    for i = 1 : size(Population,1)
                    	Population(i,:) = Population(i,:)./norm(Population(i,:));
                    end
            end
            Output = Population.*repmat((F.^(0:M - 1)), [size(Population,1) 1]);
    end
end

function W = T_uniform(k,M)
    H = floor((k*prod(1:M-1))^(1/(M-1)));
    while nchoosek(H+M-1,M-1) >= k && H > 0
        H = H-1;
    end
    if nchoosek(H+M,M-1) <= 2*k || H == 0
        H = H+1;
    end
    k = nchoosek(H+M-1,M-1);
    Temp = nchoosek(1:H+M-1,M-1)-repmat(0:M-2,nchoosek(H+M-1,M-1),1)-1;
    W = zeros(k,M);
    W(:,1) = Temp(:,1)-0;
    for i = 2 : M-1
        W(:,i) = Temp(:,i)-Temp(:,i-1);
    end
    W(:,end) = H-Temp(:,end);
    W = W/H;
end

function W = T_repeat(k,M)
    if M > 1
        k = (ceil(k^(1/M)))^M;
        Temp = 0:1/(k^(1/M)-1):1;
        code = '[c1';
        for i = 2 : M
            code = [code,',c',num2str(i)];
        end
        code = [code,']=ndgrid(Temp);'];
        eval(code);
        code = 'W=[c1(:)';
        for i = 2 : M
            code = [code,',c',num2str(i),'(:)'];
        end
        code = [code,'];'];
        eval(code);
    else
        W = [0:1/(k-1):1]';
    end
end

function FunctionValue = T_sort(FunctionValue)
    Choose = true(1,size(FunctionValue,1));
    [~,rank] = sortrows(FunctionValue);
    for i = rank'
        for j = rank(find(rank==i)+1:end)'
            if Choose(j)
                k = 1;
                for m = 2 : size(FunctionValue,2)
                    if FunctionValue(i,m) > FunctionValue(j,m)
                        k = 0;
                        break;
                    end
                end
                if k == 1
                    Choose(j) = false;
                end
            end
        end
    end
    FunctionValue = FunctionValue(Choose,:);
end