function Pred=SurrogatePrediction(x0,model)
md=model.md;
check3=model.check3;
P=model.P;
MaxIntOrder=model.MaxIntOrder;
x0=MultivariateLegendre2(x0,P,MaxIntOrder);
x0=x0(:,check3);
Pred=x0*md;
