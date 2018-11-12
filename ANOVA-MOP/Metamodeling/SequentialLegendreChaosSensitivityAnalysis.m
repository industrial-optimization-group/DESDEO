function Data=SequentialLegendreChaosSensitivityAnalysis(ProbName,ObjInd,ObjNum,lb,ub,MaxNumFunEval)
%
% This is an implementation of the method developed in 
% "M. Tan. Sequential Bayesian polynomial chaos model selection for estimation of
% sensitivity indices. SIAM/ASA Journal on Uncertainty Quantification, 3:146–168,
% 2015."
%
% For any question regarding this code, please contact
% matthtan@cityu.edu.hk.
%

global X W Y2 mY n M d M2 P Nf F R00 gamma0 gamma r lrho
global alpha E AnovaIndicators Lambda
global Gd Sigma2Est md check3 MaxIntOrder
% global Filename NI
% tic

format short g
%Dimension of problem
load d;
%Maximum polynomial degree of orthonormal polynomial regressors
P=5;
%Maximum order of ANOVA functional components to allow in regression
MaxIntOrder=d;
%Results will be written into an Excel file with the given filename
% Filename=[ProbName '_Obj_' num2str(ObjInd) , '.xlsx'];

%Compute initial sample size
P0=4;
if(d>1)
    n0=1+P0*d+ceil((nchoosek(d,2)*(P0-1)*P0/2)/d);
else
    n0=1+P0;
end
%Number of runs to add at each iteration
nadd=2*d;

%Set tolerances
Tolerance3=15;
Tolerance1=10;
Tolerance2=15;

%Prior parameters in Bayesian model
rho=0.5;
gamma0=10^4;
gamma=240;
r=0.6;
lrho=log(rho);

%Parameters for sequential procedure, h2>=h1>=2
h1=2;
h2=3;

%Program only returns information on Sobol indices up to the order given by truncate
truncate=d;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Generate initial design
n=n0;
QuasiMC=sobolset(d);
QuasiMC=scramble(QuasiMC,'MatousekAffineOwen');
D=net(QuasiMC,n)*2-1;

QuasiMCResampling=sobolset(d);
QuasiMCResampling=scramble(QuasiMCResampling,'MatousekAffineOwen');
ReSampleIndex=1;
%Evaluate function at initial design points

Y=MyFun(D,lb,ub,ProbName,ObjInd,ObjNum);

%Generate regressors
[X, alpha, AnovaIndicators, Lambda]=MultivariateLegendre(D,P,MaxIntOrder);
Nf=size(AnovaIndicators,1);
M=size(X,2);
M2=M-1;
%Interaction order and number of levels for each component of delta
E=sum(AnovaIndicators,2)';
F=P-E+2;
%Number of Sobol indices to compute
NI=sum(E<=truncate);

%Starting models for global search
if((d>1)&&(P>5))
    NoStart0=2^d-1+2^d-1-d;
    deltastart0=zeros(NoStart0,Nf);
    deltastart0(1:d,1:d)=P*speye(d);
    No=d;
    for i=2:d
        Factors=combnk(1:d,i);
        NoFactors=size(Factors,1);
        for j=1:NoFactors
            Include=((E-sum(AnovaIndicators(:,Factors(j,:)),2)')==0)&(E<=2);
            No=No+1;
            deltastart0(No,Include)=P;
            No=No+1;
            deltastart0(No,Include)=2;
        end
    end
elseif((d>1)&&(P<=5))
    NoStart0=2^d-1;
    deltastart0=zeros(NoStart0,Nf);
    deltastart0(1:d,1:d)=P*speye(d);
    No=d;
    for i=2:d
        Factors=combnk(1:d,i);
        NoFactors=size(Factors,1);
        for j=1:NoFactors
            Include=((E-sum(AnovaIndicators(:,Factors(j,:)),2)')==0)&(E<=2);
            No=No+1;
            deltastart0(No,Include)=P;
        end
    end
elseif(d==1)
    deltastart0=(0:P)';
    NoStart0=P+1;
end

%Initialize some variables
iteration=0;
stop=0;
StoremdMinusEta=zeros(1,M);
while(stop==0)
    
    if(iteration>0)
        %Add the best model found in the previous
        %iteration to the set of starting models
        if(min(pdist2(BestModel(iteration,:),deltastart0))>0.5)
            deltastart=[deltastart0; BestModel(iteration,:)];
            NoStart=NoStart0+1;
        end
    else
        deltastart=deltastart0;
        NoStart=NoStart0;
    end
    if(n>n0)
        XAdd=MultivariateLegendre2(D((n-nadd+1):n,:),P,MaxIntOrder);
        X=[X; XAdd];
    end
    
    %Compute the centered response used in model selection
    mY=mean(Y);
    Y2=Y-X(:,1)*mY;
    
    %Precompute some matrices to speed up computation of Q(delta)
    W=X(:,2:M);
    W2W2T0=gamma0*X(:,1)*X(:,1)';
    for i=1:M2
        W(:,i)=W(:,i)*sqrt(gamma*r^(Lambda(2,i)-1));
    end
    R00=W2W2T0+speye(n);
    
    %Global search
    deltaopt=zeros(NoStart,Nf);
    Q=zeros(NoStart,1);
    disp(['Total number of starting points is ' num2str(NoStart) '.'])
    for i=1:NoStart
        [deltaopt(i,:), Q(i)]=Search(deltastart(i,:));
        disp(['Objective=' num2str(ObjInd) '. Function evaluation= ' num2str(n) '. Iteration=',num2str(iteration),'. Global search from ' num2str(i) '/',num2str(NoStart),' starting points completed.'])
        %     disp(['Global search from ' num2str(i) ' starting points completed.'])
    end
    iteration=iteration+1;
    [MinQ, IndexMinQ]=min(Q);
    BestModel(iteration,:)=deltaopt(IndexMinQ,:);
    
    display('Best model found')
    disp(BestModel(iteration,:))
    
    %Precompute quantities needed in computing credible limits
    delta=BestModel(iteration,:);
    check=Lambda(2,:)<=delta(Lambda(1,:));
    check2=find(check);
    check3=[1 check2+1];
    R=R00+W(:,check2)*W(:,check2)';
    IR=invandlogdet(R);
    S=[gamma0 gamma*(r.^(Lambda(2,:)-1))];
    S=diag(S(check3));
    XS=X(:,check3)*S;
    Gd=S-(XS')*IR*XS;
    RSS=(Y2')*IR*Y2;
    Sigma2Est=RSS/n;
    md=[mY; zeros(length(check2),1)]+XS'*IR*Y2;
    StoremdMinusEta(iteration,check3)=md-[mY; zeros(length(check2),1)];
    weights=1./diag(IR);
    PredCriterion1(iteration,1)=sqrt(mean((weights.*(Y-X(:,check3)*md)).^2))/std(Y,1)*100;
    display('RMS of leave-one-out prediction errors/Standard deviation of Y (in percent)')
    disp(PredCriterion1(iteration,1))
    
    %Check if stopping conditions have been met
    if((iteration>=h1))
        CheckPredAccuracy=(PredCriterion1(iteration,1)<Tolerance1)&(PredCriterion2(iteration-1,1)<Tolerance2);
        PercentChangeInBetaEst=sqrt(max(sum((StoremdMinusEta((iteration-h1+1):(iteration-1),:)-StoremdMinusEta((iteration-h1+2):iteration,:)).^2,2)))/sqrt(sum(StoremdMinusEta(iteration,:).^2))*100
        CheckPercentChangeInBetaEst=PercentChangeInBetaEst<Tolerance3;
        if(CheckPredAccuracy&&CheckPercentChangeInBetaEst)
            stop=1;
            display('Procedure terminated. Changes in posterior mean of regression coefficients are small and prediction criteria are less than tolerances.')
        end
    end
    if((stop==0)&&(iteration>=h2))
        PercentChangeInBetaEst=sqrt(max(sum((StoremdMinusEta((iteration-h2+1):(iteration-1),:)-StoremdMinusEta((iteration-h2+2):iteration,:)).^2,2)))/sqrt(sum(StoremdMinusEta(iteration,:).^2))*100
        CheckPercentChangeInBetaEst=PercentChangeInBetaEst<Tolerance3;
        if(CheckPercentChangeInBetaEst)
            stop=1;
            display('Procedure terminated. Changes in posterior mean of regression coefficients are small but prediction criterion/criteria does/do not meet tolerance(s).')
        end
    end
    
    % if iteration>=8
    %     stop=1;
    %     display('Maximum iteration is reached');
    % end
    if n>=MaxNumFunEval
        stop=1;
        display('Maximum number of function evaluations is reached')
    end
    
    if(stop==0)
        
        %Next design point is set to the next nadd Sobol quasi random points
        NextDesignPoints=net(QuasiMC,n+nadd);
        NextDesignPoints=NextDesignPoints((n+1):(n+nadd),:)*2-1;
        
        %Evaluate true function at new design points
        NewObservations=MyFun(NextDesignPoints,lb,ub,ProbName,ObjInd,ObjNum);
        
        %Compute predictions for new design points
        predictions=Pred(NextDesignPoints);
        
        %Update design and vector of function evaluations
        D=[D; NextDesignPoints];
        Y=[Y; NewObservations];
        %Increase n by nadd
        n=n+nadd;
        
        %Evaluate standard deviation of prediction errors and
        RMSPredErr=sqrt(mean((NewObservations-predictions).^2));
        display('RMS of prediction errors/Standard deviation of Y (in percent)')
        PredCriterion2(iteration,1)=RMSPredErr/std(Y,1)*100;
        disp(PredCriterion2(iteration,1))
        
    end
end

% display('Value of P')
% disp(P)
% display('Initial design size')
% disp(n0)
% display('Final design size')
% disp(n)

StoreData=[D Y];
% display('Final design and observations')
% disp(StoreData)

StoreBestModels=[(1:iteration)' BestModel];
% display('Iteration number, and best model for each iteration')
% disp(StoreBestModels)
% display('ANOVA decomposition index (maps each component of delta to the functional ANOVA component it represents)')
% disp(AnovaIndicators)

StorePredictionInfo=[(1:iteration)' PredCriterion1 [PredCriterion2; -1]];
% display('Iteration number, prediction criterion 1, prediction criterion 2')
% disp(StorePredictionInfo)

% xlswrite(Filename,{'d, initial design size, final design size, P, maximum order of interactions, tolerance 3, tolerance 1, tolerance 2, rho, gamma0, gamma, r'},'1','A1')
% xlswrite(Filename,[d n0 n P MaxIntOrder Tolerance3 Tolerance1 Tolerance2 rho gamma0 gamma r],'1','A2')
% 
% xlswrite(Filename,{'Set of starting models'},'M_0','A1')
% xlswrite(Filename,deltastart0,'M_0','A2')
% 
% xlswrite(Filename,{'Final design and observations'},'1','A4')
% xlswrite(Filename,StoreData,'1','A5')

% xlswrite(Filename,{'Iteration number and best model for each iteration'},'2','A1')
% xlswrite(Filename,StoreBestModels,'2','A2')
% xlswrite(Filename,{'ANOVA decomposition index (maps each component of delta to the functional ANOVA component it represents)'},'2',['A' num2str(iteration+3)])
% xlswrite(Filename,AnovaIndicators*1,'2',['A' num2str(iteration+4)])
% 
% xlswrite(Filename,{'Iteration number, prediction criterion 1, prediction criterion 2'},'3','A1')
% xlswrite(Filename,StorePredictionInfo,'3','A2')

Data.md=md;
Data.check3=check3;
Data.P=P;
Data.MaxIntOrder=MaxIntOrder;
Data.D=D;
Data.Y=Y;
Data.iteration=iteration;

if(d>1)
    TotalIndices=SimulateSobolIndices(BestModel(iteration,:));
    Data.TotalIndices=TotalIndices;
end
% toc

function Pred=Pred(x0)
global md check3 P MaxIntOrder
x0=MultivariateLegendre2(x0,P,MaxIntOrder);
x0=x0(:,check3);
Pred=x0*md;

function [Model, Q]=Search(delta)
global Nf

localoptimum=0;
while(localoptimum==0)
    olddelta=delta;
    [oldm2lprob, IR, LDR]=calculatem2lprob2(olddelta);
    for i=1:Nf
        [m2lprob, values, storeIR, storeLDR]=calculatem2lprob(delta,i,oldm2lprob,IR,LDR);
        [Minm2lprob, index]=min(m2lprob);
        delta(i)=values(index);
        oldm2lprob=Minm2lprob;
        IR=storeIR{index};
        LDR=storeLDR(index);
    end
    if(sum(olddelta==delta)==Nf)
        localoptimum=1;
    end
end
Model=delta;
Q=oldm2lprob;

function [calculatem2lprob, values, storeIR, storeLDR]=calculatem2lprob(delta0,I,m2lprob0,IR,LDR)
global W Y2 d n P Nf F  lrho
global E Lambda

delta=delta0;
values=[0 E(I):P];
storeIR=cell(1,F(I));
storeLDR=zeros(1,F(I));
calculatem2lprob=Inf*ones(1,F(I));
index=find(abs(values-delta(I))<0.5);
calculatem2lprob(index)=m2lprob0;
storeIR{index}=IR;
storeLDR(index)=LDR;

check0=Lambda(2,:)<=delta(Lambda(1,:));
check20=find(check0);
logpdelta0=sum(delta(1:d)*lrho)+sum((max(delta(d+1:Nf)-E(d+1:Nf)+1,0)).*E(d+1:Nf)*lrho);

check2=check20;
logpdelta=logpdelta0;
for k=(index+1):F(I)
    oldcheck=check2;
    delta(I)=values(k);
    check=Lambda(2,:)<=delta(Lambda(1,:));
    check2=find(check);
    newcheck=setdiff(check2,oldcheck);
    L=length(newcheck);
    T=speye(L)+(W(:,newcheck)')*IR*W(:,newcheck);
    T2=(W(:,newcheck)')*IR;
    [IT, LDT]=invandlogdet(T);
    IR=IR-T2'*IT*T2;
    LDR=LDT+LDR;
    storeIR{k}=IR;
    storeLDR(k)=LDR;
    RSS=(Y2')*IR*Y2;
    logpdelta=logpdelta+E(I)*lrho;
    m2lprob=n*log(RSS)+LDR-2*logpdelta;
    calculatem2lprob(k)=m2lprob;
end

check2=check20;
logpdelta=logpdelta0;
IR=storeIR{index};
LDR=storeLDR(index);
for k=(index-1):-1:1
    oldcheck=check2;
    delta(I)=values(k);
    check=Lambda(2,:)<=delta(Lambda(1,:));
    check2=find(check);
    newcheck=setdiff(oldcheck,check2);
    L=length(newcheck);
    T=speye(L)-(W(:,newcheck)')*IR*W(:,newcheck);
    T2=(W(:,newcheck)')*IR;
    [IT, LDT]=invandlogdet(T);
    IR=IR+T2'*IT*T2;
    LDR=LDT+LDR;
    storeIR{k}=IR;
    storeLDR(k)=LDR;
    RSS=(Y2')*IR*Y2;
    logpdelta=logpdelta-E(I)*lrho;
    m2lprob=n*log(RSS)+LDR-2*logpdelta;
    calculatem2lprob(k)=m2lprob;
end

function [calculatem2lprob, storeIR, storeLDR]=calculatem2lprob2(delta)
global W Y2 d n Nf R00 lrho
global E Lambda

check=Lambda(2,:)<=delta(Lambda(1,:));
check2=find(check);
R=R00+W(:,check2)*W(:,check2)';
[IR, LDR]=invandlogdet(R);
storeIR=IR;
storeLDR=LDR;
RSS=(Y2')*IR*Y2;
logpdelta=sum(delta(1:d)*lrho)+sum((max(delta(d+1:Nf)-E(d+1:Nf)+1,0)).*E(d+1:Nf)*lrho);
calculatem2lprob=n*log(RSS)+LDR-2*logpdelta;

function [invR, logdetR]=invandlogdet(R)

CR=chol(R);
ICR=inv(CR);
invR=ICR*(ICR');
logdetR=2*sum(log(diag(CR)));

function TotalIndices=SimulateSobolIndices(model)
global X W Y2 mY d n M2 Nf R00 gamma0 gamma r
global AnovaIndicators Lambda
global SobolIndices TotalSensitivityIndices I Type quantile
global Filename NI

SampleSize0=100;
delta=model;
check=Lambda(2,:)<=delta(Lambda(1,:));
check2=find(check);
check3=[1 check2+1];
L=length(check3);

if(L==1)
%     display('ANOVA Decomposition Index (columns 1:d), Probability=0, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile) for Sobol Indices')
    Sobol=[AnovaIndicators(1:NI,:) [ones(NI,1) zeros(NI,3)]];
%     disp(Sobol)
%     xlswrite(Filename,{'ANOVA Decomposition Index (columns 1:d), Probability=0, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile) for Sobol Indices'},'SobolIndices','A1')
%     xlswrite(Filename,Sobol,'SobolIndices','A2')
    
%     display('Probability=0, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile) for Total Sensitivity Indices')
    Total=[ones(d,1) zeros(d,3)];
%     disp(Total)
%     xlswrite(Filename,{'Probability=0, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile) for Total Sensitivity Indices'},'TotalSensitivityIndices','A1')
%     xlswrite(Filename,Total,'TotalSensitivityIndices','A2')
    return
end

R=R00+W(:,check2)*W(:,check2)';
IR=invandlogdet(R);
S=[gamma0 gamma*(r.^(Lambda(2,:)-1))];
S=diag(S(check3));
XS=X(:,check3)*S;
Gd=S-(XS')*IR*XS;
RSS=(Y2')*IR*Y2;
scale=Gd*(RSS/n);
md=[mY; zeros(L-1,1)]+XS'*IR*Y2;
[cholscaleT, error]=chol(scale);
cholscaleT=cholscaleT';
if(error~=0)
    [eigvec, eigval]=svd(scale);
    cholscaleT=eigvec*sqrt(eigval)*eigvec';
end

OldSampleSize=0;
NewSampleSize=SampleSize0;
stop=0;

SobolIndices=cell(NI,1);
TotalSensitivityIndices=cell(d,1);
coeffind=cell(NI,1);
coeffind2=cell(d,1);
for j=1:NI
    coeffind{j}=Lambda(1,:)==j;
end
for j=1:d
    Indicator=AnovaIndicators(:,j);
    coeffind2{j}=zeros(1,M2);
    for i=1:Nf
        if(Indicator(i)>0)
            coeffind2{j}=(coeffind2{j}+(Lambda(1,:)==i))>0;
        end
    end
end

while(stop==0)
    
    for k=(OldSampleSize+1):NewSampleSize
        
        beta=zeros(M2,1);
        sample=cholscaleT*normrnd(0,1,L,1)/sqrt(chi2rnd(n)/n)+md;
        beta(check2,1)=sample(2:L);
        SSbeta=sum(beta.^2);
        
        for j=1:NI
            SobolIndices{j}(k)=sum(beta(coeffind{j}).^2)/SSbeta;
        end
        
        for j=1:d
            TotalSensitivityIndices{j}(k)=sum(beta(coeffind2{j}).^2)/SSbeta;
        end
        
    end
    
    Est=zeros(NI,1);
    VarianceEst=zeros(NI,1);
    Variance=zeros(NI,1);
    for j=1:NI
        Est(j)=mean(SobolIndices{j});
        Variance(j)=var(SobolIndices{j});
        VarianceEst(j)=Variance(j)/NewSampleSize;
    end
    Stderr=sqrt(VarianceEst);
    
    Est2=zeros(d,1);
    VarianceEst2=zeros(d,1);
    Variance2=zeros(d,1);
    for j=1:d
        Est2(j)=mean(TotalSensitivityIndices{j});
        Variance2(j)=var(TotalSensitivityIndices{j});
        VarianceEst2(j)=Variance2(j)/NewSampleSize;
    end
    Stderr2=sqrt(VarianceEst2);
    
    if(all(Stderr<=0.00025)&&all(Stderr2<=0.00025))
        stop=1;
    else
        TotalSampleSizeNeeded=max([Variance; Variance2]/0.00025^2);
        OldSampleSize=NewSampleSize;
        NewSampleSize=ceil(TotalSampleSizeNeeded);
    end
    
end

LCL=zeros(NI,1);
UCL=zeros(NI,1);
Pr0=zeros(NI,1);
Pr1=zeros(NI,1);
STD=sqrt(Variance);
Type=1;
for I=1:NI
    Pr0(I)=CDFEst(5*10^-4);
    Pr1(I)=1-CDFEst(1-5*10^-4);
    if(STD(I)>=(1.25*10^-4))
        if(Pr0(I)>0.025)
            LCL(I)=0;
        else
            quantile=0.025;
            LCL(I)=fzero(@CdfDev,max(Est(I)-STD(I),0));
        end
        if(Pr1(I)>0.025)
            UCL(I)=1;
        else
            quantile=0.975;
            UCL(I)=fzero(@CdfDev,min(Est(I)+STD(I),1));
        end
    else
        LCL(I)=Est(I);
        UCL(I)=Est(I);
    end
end

LCL2=zeros(d,1);
UCL2=zeros(d,1);
Pr0_2=zeros(d,1);
Pr1_2=zeros(d,1);
STD2=sqrt(Variance2);
Type=2;
for I=1:d
    Pr0_2(I)=CDFEst(5*10^-4);
    Pr1_2(I)=1-CDFEst(1-5*10^-4);
    if(STD2(I)>=(1.25*10^-4))
        if(Pr0_2(I)>0.025)
            LCL2(I)=0;
        else
            quantile=0.025;
            LCL2(I)=fzero(@CdfDev,max(Est2(I)-STD2(I),0));
        end
        if(Pr1_2(I)>0.025)
            UCL2(I)=1;
        else
            quantile=0.975;
            UCL2(I)=fzero(@CdfDev,min(Est2(I)+STD2(I),1));
        end
    else
        LCL2(I)=Est2(I);
        UCL2(I)=Est2(I);
    end
end

% display('ANOVA decomposition index (columns 1:d), Probability<=0.0005, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile), Probability>=0.9995 for Sobol Indices')
% display('All values (except the ANOVA decomposition index, which are binary numbers) are rounded to three decimal places')
Sobol=[AnovaIndicators(1:NI,:) round([Pr0 LCL Est UCL Pr1]*10^3)/10^3];
% disp(Sobol)
% xlswrite(Filename,{'ANOVA decomposition index (columns 1:d), Probability<=0.0005, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile), Probability>=0.9995 for Sobol Indices'},'SobolIndices','A1')
% xlswrite(Filename,{'All values (except the ANOVA decomposition indices, which are binary numbers) are rounded to three decimal places'},'SobolIndices','A2')
% xlswrite(Filename,Sobol,'SobolIndices','A3')

% display('Probability<=0.0005, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile), Probability>=0.9995 for Total Sensitivity Indices')
% display('All values are rounded to three decimal places')
Total=round([Pr0_2 LCL2 Est2 UCL2 Pr1_2]*10^3)/10^3;
% disp(Total)
TotalIndices=Total(:,2:end-1);
% xlswrite(Filename,{'Probability<=0.0005, LCL (0.025 Quantile), Mean, UCL (0.975 Quantile), Probability>=0.9995 for Total Sensitivity Indices'},'TotalSensitivityIndices','A1')
% xlswrite(Filename,{'All values are rounded to three decimal places'},'TotalSensitivityIndices','A2')
% xlswrite(Filename,Total,'TotalSensitivityIndices','A3')

function CdfDev=CdfDev(x)
global quantile
CdfDev=CDFEst(x)-quantile;

function CDFEst=CDFEst(x)
global SobolIndices TotalSensitivityIndices I Type
if(x<0)
    CDFEst=0;
    return
elseif(x>=1)
    CDFEst=1;
    return
end

if(Type==1)
    CDFEst=PiecewiseLinearCDF(x,SobolIndices{I});
elseif(Type==2)
    CDFEst=PiecewiseLinearCDF(x,TotalSensitivityIndices{I});
end

function PiecewiseLinearCDF=PiecewiseLinearCDF(x,data)

[Fi,xi] = ecdf(data);
nxi=length(xi);
if(nxi<=2)
    PiecewiseLinearCDF=xi(1)<=x;
else
    nxi=nxi-1;
    xj = xi(2:end);
    Fj = (Fi(1:(end-1))+Fi(2:end))/2;
    MinPoint=max(xj(1)-Fj(1)*(xj(2)-xj(1))/((Fj(2)-Fj(1))),0);
    MaxPoint=min(xj(nxi)+(1-Fj(nxi))*((xj(nxi)-xj(nxi-1))/(Fj(nxi)-Fj(nxi-1))),1);
    xj = [MinPoint; xj; MaxPoint];
    Fj = [0; Fj; 1];
    index=sum(xj<=x);
    if(index==0)
        PiecewiseLinearCDF=0;
    elseif(index==(nxi+2))
        PiecewiseLinearCDF=1;
    else
        PiecewiseLinearCDF=Fj(index)+(Fj(index+1)-Fj(index))/(xj(index+1)-xj(index))*(x-xj(index));
    end
end