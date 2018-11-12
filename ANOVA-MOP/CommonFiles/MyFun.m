function Value=MyFun(X0,lb,ub,ProbName,ObjInd,ObjNum)
range=ub-lb;
n=size(X0,1);
X=((X0+1).*repmat(range,n,1))/2+repmat(lb,n,1);
fTemp=P_objective('value',ProbName,ObjNum,X);
Value=fTemp(:,ObjInd);
end
