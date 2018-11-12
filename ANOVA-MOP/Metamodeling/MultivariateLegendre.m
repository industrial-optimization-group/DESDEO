function [MultivariateLegendre, storealpha, AnovaIndicators, Lambda]=MultivariateLegendre(D,P,MaxIntOrder)

[n,d]=size(D);
M=nchoosek(d+P,d);
storealpha=zeros(M-1,d);
MultivariateLegendre=ones(n,M);

if(d==1)
    MultivariateLegendre=orthonormal_polynomial_legendre(P,D);
    storealpha=(1:P)';    
    AnovaIndicators=ones(P,1);
    Lambda=zeros(2,P);
    Lambda(1,:)=1;
    Lambda(2,:)=storealpha;
    return
end

if((nargin<3)||(MaxIntOrder<1)||(MaxIntOrder>min(d,P)))
    MaxIntOrder=min(d,P);
else
    MaxIntOrder=round(MaxIntOrder);
end

PolynomialEvals=cell(1,d);
for j=1:d
PolynomialEvals{j}=orthonormal_polynomial_legendre(P,D(:,j));
MultivariateLegendre(:,1)=MultivariateLegendre(:,1).*PolynomialEvals{j}(:,1);
end

Nf=2^d-1;
for i=MaxIntOrder+1:d
    Nf=Nf-nchoosek(d,i);
end

AnovaIndicators=zeros(Nf,d);
Lambda=zeros(2,M-1);
r=0;
t=1;
u=0;
for j=1:MaxIntOrder
    Combinations=combnk(1:d,j);
    Combinations=sortrows(Combinations,1:j);
    No=size(Combinations,1); 
    alpha2=combnk(1:P,j);
    No2=size(alpha2,1);
    alpha=zeros(No2,j);
    alpha(:,1)=alpha2(:,1);
    for i=2:j
        alpha(:,i)=alpha2(:,i)-alpha2(:,i-1);
    end
    alpha=sortrows(alpha,1:j);
    for k=1:No   
        for l=1:No2
        t=t+1;
            for i=1:j
            MultivariateLegendre(:,t)=MultivariateLegendre(:,t).*PolynomialEvals{Combinations(k,i)}(:,alpha(l,i)+1);
            end
        end
        r=r+1;
        AnovaIndicators(r,Combinations(k,:))=1;     
        u2=u+No2;
        storealpha(u+1:u2,Combinations(k,:))=alpha;
        Lambda(1,u+1:u2)=r;
        u=u2;
    end
end
Lambda(2,:)=sum(storealpha,2)';
AnovaIndicators=logical(AnovaIndicators);
MultivariateLegendre=MultivariateLegendre(:,1:t);
storealpha=storealpha(1:u,:);
Lambda=Lambda(:,1:u);