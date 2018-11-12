function P_output (Population,time,Algorithm,Problem,M,Run)

FunctionValue = P_objective('value',Problem,M,Population);
if(strcmp(Algorithm, 'cRVEA'))
    FunctionValue = FunctionValue(:,1:end - 1);
end;
% TrueValue = P_objective('true',Problem,M,1000);

NonDominated  = P_sort(FunctionValue,'first')==1;
Population    = Population(NonDominated,:);
FunctionValue = FunctionValue(NonDominated,:);

if(M == 2)
%     plot(TrueValue(:,1), TrueValue(:,2),'.');
    hold on;
    plot(FunctionValue(:,1), FunctionValue(:,2), 'ro', 'MarkerFace', 'r');
    xlim([0 max(FunctionValue(:,1)) + 0.1]);
    ylim([0 max(FunctionValue(:,2)) + 0.1]);
    xlabel('f_1');ylabel('f_2');
    hold off;
else
    plot3(TrueValue(:,1), TrueValue(:,2), TrueValue(:,3), '.');
    hold on;
    plot3(FunctionValue(:,1), FunctionValue(:,2), FunctionValue(:,3), 'ro','MarkerFace', 'r');
    xlim([0 max(TrueValue(:,1)) + 0.1]);
    ylim([0 max(TrueValue(:,2)) + 0.1]);
    zlim([0 max(TrueValue(:,3)) + 0.1]);
    xlabel('f_1', 'FontSize', 14);ylabel('f_2', 'FontSize', 14);zlabel('f_3', 'FontSize', 14);
    view(135, 30);
    hold off;
end;

eval(['save Data/',Algorithm,'/',Algorithm,'_',Problem,'_',num2str(M),'_',num2str(Run),' Population FunctionValue time'])
end


