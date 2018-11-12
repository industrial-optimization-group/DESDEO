function buildingblocks=buildingblocks(X0,Coefficients,Choice)
    
    [n, d]=size(X0);
    X=(X0+1)/2;

    L=size(Choice,1);
    buildingblocks=0;
    for i=1:L
        Int=find(Choice(i,3:d+2));
        if(Choice(i,2)==1)
            Xint=prod(X(:,Int),2);
        else
            Xint=mean(X(:,Int),2);
        end
        buildingblocks=buildingblocks+Coefficients(i)*subfunction(Xint,Choice(i,1));
    end

function subfunction=subfunction(x,no)
        
if(no==1)
    subfunction=x;           
elseif(no==2)
    subfunction=(2*x-1).^2;   
elseif(no==3)
    subfunction=sin(2*pi()*x)./(2-sin(2*pi()*x));        
elseif(no==4)
    subfunction=0.1*sin(2*pi()*x)+0.2*cos(2*pi()*x)+0.3*sin(2*pi()*x).^2+0.4*cos(2*pi()*x).^3+0.5*sin(2*pi()*x).^3;        
end