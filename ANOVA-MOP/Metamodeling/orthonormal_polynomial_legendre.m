function v=orthonormal_polynomial_legendre(p,x)

nn=(1:p)';
b=[1; ((nn).^2)./((2*nn-1).*(2*nn+1))];
sqrtb=sqrt(b);

n=size(x,1);
if(p<0)
    v=[];
return
end

v=zeros(n,p+1);
v(:,1)=1/sqrtb(1);

if(p<1)
    return
end

v(:,2)=x.*v(:,1)/sqrtb(2);

for i=2:p 
    v(:,i+1)=(x.*v(:,i)-sqrtb(i)*v(:,i-1))/sqrtb(i+1);
end