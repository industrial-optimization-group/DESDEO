function MultivariateLegendre2=MultivariateLegendre2(D,P,MaxIntOrder)

[n,d]=size(D);
M=nchoosek(d+P,d);
MultivariateLegendre2=ones(n,M);

if(d==1)
    MultivariateLegendre2=orthonormal_polynomial_legendre(P,D);
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
MultivariateLegendre2(:,1)=MultivariateLegendre2(:,1).*PolynomialEvals{j}(:,1);
end

t=1;
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
            MultivariateLegendre2(:,t)=MultivariateLegendre2(:,t).*PolynomialEvals{Combinations(k,i)}(:,alpha(l,i)+1);
            end
        end
    end
end
MultivariateLegendre2=MultivariateLegendre2(:,1:t);