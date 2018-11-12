%This file includes the original and scaled DTLZ1 to DTLZ4

function [Output,Boundary,Coding] = P_objective(Operation,Problem,M,Input, ... 
    SubProblemObjectiveIndices,SubProblemVariablesIndices,NumVar,Bounds,lb,ub,FixedIndices, FixedValues, model)
k = find(~isstrprop(Problem,'digit'),1,'last');
    switch Problem(1:k)
        case 'ZDT'
            [Output,Boundary,Coding]=P_ZDT(Operation,Problem,Input);
        case 'DTLZ'
            [Output,Boundary,Coding] = P_DTLZ(Operation,Problem,M,Input);
        case 'SDTLZ'
            [Output,Boundary,Coding] = P_SDTLZ(Operation,Problem,M,Input);
        case 'ALBERTO'
            [Output,Boundary,Coding] = P_ALBERTO(Operation,Input);
        case 'Surrogate'
            [Output,Boundary,Coding] = P_Surrogate(Operation,M,Input, ...
                SubProblemObjectiveIndices,SubProblemVariablesIndices,NumVar,Bounds,lb,ub,FixedIndices, FixedValues, model);            
        otherwise
            error([Problem,'Not Exist']);
    end
end

function [Output,Boundary,Coding] = P_Surrogate(Operation,M,Input, ... 
    SubProblemObjectiveIndices,SubProblemVariablesIndices,NumVar,Bounds,lb,ub,FixedIndices, FixedValues, model)
Boundary = NaN; Coding = NaN;
switch Operation
    %Population Initialization
    case 'init'
        D = NumVar;
        MaxValue   = Bounds(1,:);
        MinValue   = Bounds(2,:);
        Population = rand(Input,D);
        Population = Population.*repmat(MaxValue,Input,1)+(1-Population).*repmat(MinValue,Input,1);        
        Output   = Population;
        Boundary = [MaxValue;MinValue];
        Coding   = 'Real';
    case 'value'
        NumPop=size(Input,1);
        InputTemp=zeros(NumPop,length(SubProblemVariablesIndices)+length(FixedIndices));
        InputTemp(:,FixedIndices)=repmat(FixedValues,NumPop,1);
        InputTemp(:,SubProblemVariablesIndices)=Input; 
        Input = MapSamples(InputTemp,[-ones(1,length(lb));ones(1,length(lb))],[lb;ub]);
        Output = zeros(NumPop,M);        
        for objective=1:M
            Output(:,objective)=SurrogatePrediction(Input,model(SubProblemObjectiveIndices(objective)));
        end
end

end

function [Output,Boundary,Coding] =P_ALBERTO(Operation,Input)
Boundary = NaN; Coding = NaN;
switch Operation
    %Population Initialization
    case 'init'
        numVar=5;
        Min=-ones(1,numVar);
        Max=ones(1,numVar);
        Population = rand(Input,numVar);
%         Population=((Input+1).*repmat(range,Input,1))/2+repmat(Min,Input,1);
        Population = Population.*repmat(Max,Input,1)+(1-Population).*repmat(Min,Input,1);
        Output=Population;
        Boundary=[Min;Max];
        Coding='Real';
    case 'value'
        [numSample, numVar]=size(Input);
        x=Input;
        epsilon = 0.1;
        P1 = [1 1 1];
        P2 = [1 -1 -1];
        P3 = [1 1 -1];
        
        P4=[1 -1];
        P5=[-1 1];
        
        Phi1 = sum((x(:,1:3)-ones(numSample,1)*P1).^2,2);
        Phi2 = sum((x(:,1:3)-ones(numSample,1)*P2).^2,2);
        Phi3 = sum((x(:,1:3)-ones(numSample,1)*P3).^2,2);
        Phi4 = sum((x(:,4:5)-ones(numSample,1)*P4).^2,2);
        Phi5 = sum((x(:,4:5)-ones(numSample,1)*P5).^2,2);
        
        
        Output(:,1) = Phi1 + epsilon*Phi4;
        Output(:,5) = Phi2 + epsilon*Phi5;
        Output(:,3) = Phi3 + epsilon*(Phi4 + Phi5);
        Output(:,4) = Phi4 + epsilon*Phi1;
        Output(:,2) = Phi5 + epsilon*(Phi1 + Phi2);
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
            
            D = 7;
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
                    g = 100 .* (10 + sum((Population(:,3:end) - 0.5).^2 - cos(20 * pi * (Population(:,3:end)-0.5)),2));
                    FunctionValue(:,1) = 0.5 .* Population(:,1) .* Population(:,2) .* (1 + g);
                    FunctionValue(:,2) = 0.5 .* Population(:,1) .* (1 - Population(:,2)) .* (1 + g);
                    FunctionValue(:,3) = 0.5 .* (1 - Population(:,1)) .* (1 + g);
%                     k = find(~isstrprop(Problem,'digit'),1,'last');
%                     K = [5 10 10 10 10 10 20];
%                     K = K(str2double(Problem(k+1:end)));
%                     g = 100*(K+sum((Population(:,M:end)-0.5).^2-cos(20.*pi.*(Population(:,M:end)-0.5)),2));
%                     for i = 1 : M
%                         FunctionValue(:,i) = 0.5.*prod(Population(:,1:M-i),2).*(1+g);
%                         if i > 1
%                             FunctionValue(:,i) = FunctionValue(:,i).*(1-Population(:,M-i+1));
%                         end
%                     end
                case 'DTLZ2'
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'DTLZ3'               
                    g = 100*(size(Population(:,M:end),2) + ...
                        sum((Population(:,M:end)-0.5).^2 - cos(20*pi*(Population(:,M:end)-0.5)),2));
%                     FunctionValue(:,1) = (1+g) .* cos(Population(:,1) * pi/2) .* cos(Population(:,2) * pi/2);
%                     FunctionValue(:,2) = (1+g) .* cos(Population(:,1) * pi/2) .* sin(Population(:,2) * pi/2);
%                     FunctionValue(:,3) = (1+g) .* sin(Population(:,1) * pi/2);
                    for i = 1 : M-1
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                    FunctionValue(:,M)= (1+g) .* sin(0.5.*pi.*Population(:,1));
                case 'DTLZ4'
                    Population(:,1:M-1) = Population(:,1:M-1).^100;
                    g = sum((Population(:,M:end)-0.5).^2,2);
                    for i = 1 : M
                        FunctionValue(:,i) = (1+g).*prod(cos(0.5.*pi.*Population(:,1:M-i)),2);
                        if i > 1
                            FunctionValue(:,i) = FunctionValue(:,i).*sin(0.5.*pi.*Population(:,M-i+1));
                        end
                    end
                case 'DTLZ5'
                    Xm = Population(:,3:end);
                    
                    theta1 = Population(:,1) * pi/2;
                    
                    g = sum((Xm - 0.5).^2,2);
                    
                    
                    term1 = 4 * (1 + g);
                    
                    term2 = 1 + 2 .* Population(:,2) .* g;
                    
                    theta2 = (pi ./ term1) .* (term2);
                    
                    FunctionValue(:,1) = cos(theta1) .* cos(theta2) .* (1 + g);
                    FunctionValue(:,2) = cos(theta1) .* sin(theta2) .* (1 + g);
                    FunctionValue(:,3) = sin(theta1) .* (1 + g);
                case 'DTLZ6'
                    Xm = Population(:,3:end);                    
                    theta1 = Population(:,1) * pi/2;                    
                    g = sum((Xm).^(0.1),2);                                        
                    term1 = 4 * (1 + g);                    
                    term2 = 1 + 2 .* Population(:,2) .* g;                    
                    theta2 = (pi ./ term1) .* (term2);                    
                    FunctionValue(:,1) = cos(theta1) .* cos(theta2) .* (1 + g);
                    FunctionValue(:,2) = cos(theta1) .* sin(theta2) .* (1 + g);
                    FunctionValue(:,3) = sin(theta1) .* (1 + g);                                        
                case 'DTLZ7'
                    Xm = Population(:,3:end);
                    numXm = size(Xm,2);
                    g = 1 + (9 / numXm) * sum(Xm,2);
                    FunctionValue(:,1) = Population(:,1);
                    FunctionValue(:,2) = Population(:,2);
                    fixTerm1 = 1 ./ (1 + g);
                    fixTerm2(:,1) = 1 + sin(3 * pi * FunctionValue(:,1));
                    fixTerm2(:,2) = 1 + sin(3 * pi * FunctionValue(:,2));
                    h = 3 - ((FunctionValue(:,1) .* fixTerm1) .* (1 + fixTerm2(:,1)) + (FunctionValue(:,2) .* fixTerm1) .* (1 + fixTerm2(:,2)));
                    FunctionValue(:,3) = (1 + g) .* h;
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

function [Output, Boundary, Coding] =P_ZDT(Operation,Problem,Input)
Boundary = NaN; Coding = NaN;
switch Operation
    %Population Initialization
    case 'init'
        D = 7;
        MaxValue   = ones(1,D);
        MinValue   = zeros(1,D);
        Population = rand(Input,D);
        Population = Population.*repmat(MaxValue,Input,1)+(1-Population).*repmat(MinValue,Input,1);
        
        FunctionValue   = Population;
        Boundary = [MaxValue;MinValue];
        Coding   = 'Real';
    case 'value'
        Population    = Input;
        FunctionValue = zeros(size(Population,1),2);
        switch Problem            
            case 'ZDT1'
                numVar = size(Population,2);
                g = 1 + (9 / (numVar - 1)) * sum(Population(:,2:end),2);
                FunctionValue(:,1) = Population(:,1);
                FunctionValue(:,2) = g .* (1-sqrt(Population(:,1) ./ g ));
            case 'ZDT2'
                numVar = size(Population,2);
                g = 1 + (9 / (numVar - 1)) * sum(Population(:,2:end),2);
                FunctionValue(:,1) = Population(:,1);
                FunctionValue(:,2) = g .* (1 - (FunctionValue(:,1) ./ g) .^ 2);
            case 'ZDT3'
                numVar = size(Population,2);
                g = 1 + (9 / (numVar-1)) * sum(Population(:,2:numVar),2);
                fixTerm1 = 1 - sqrt(Population(:,1) ./ g);
                fixTerm2 = (Population(:,1) ./ g) .* sin(10 * pi * Population(:,1));
                FunctionValue(:,1) = Population(:,1);
                FunctionValue(:,2) = g .* (fixTerm1 - fixTerm2);
            case 'ZDT4'
                numVar = size(Input,2);
                g = 1 + 10*(numVar-1)+ sum(Population(:,2:end).^2-10*cos(4*pi*Population(:,2:end)),2);
                FunctionValue(:,1)=Population(:,1);
                FunctionValue(:,2)= g .* (1-sqrt(FunctionValue(:,1) ./ g));
            case 'ZDT6'
                numVar = size(Input,2);
                g = 1 + 9 .* (sum(Input(:,2:numVar),2) ./ (numVar-1)).^0.25;                
                FunctionValue(:,1) = 1 - exp(-4*Input(:,1)) .* sin(6*pi*Input(:,1)).^6;
                FunctionValue(:,2) = g .* (1 - (FunctionValue(:,1) ./ g).^2);
        end
        Output=FunctionValue;
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