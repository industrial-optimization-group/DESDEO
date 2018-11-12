function [asfVal]=ASF(x,StrucData)
x=x';
SurrogateData=StrucData.Surrogate;
ObjIndices=StrucData.ObjIndices;
NumObj=length(ObjIndices);
y=zeros(1,NumObj);
DecomposedBounds=StrucData.DecomposedBounds;
numPop=size(x,1);
range=DecomposedBounds(2,:)-DecomposedBounds(1,:);
x=((x+1).*repmat(range,numPop,1))/2+repmat(DecomposedBounds(1,:),numPop,1);
zref=StrucData.z;
for Objective=1:NumObj 
    y(Objective)=SurrogatePrediction(x,SurrogateData.SurrogateDataInfo(ObjIndices(Objective)));    
end

asfVal = max((y - zref))+(10^(-6))*sum(y-zref,2);
end