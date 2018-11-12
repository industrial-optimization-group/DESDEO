function Output=MapSamples(Samples,NewBounds,CurrentBounds)
[NumSamples, ~]=size(Samples);
LowerBoundNewRange=NewBounds(1,:);
UpperBoundNewRange=NewBounds(2,:);
LowerBoundOldRange=CurrentBounds(1,:);
UpperBoundOldRange=CurrentBounds(2,:);
m=(UpperBoundNewRange-LowerBoundNewRange) ./ (UpperBoundOldRange-LowerBoundOldRange);
Output=repmat(m,NumSamples,1).*(Samples-repmat(LowerBoundOldRange,NumSamples,1))+repmat(LowerBoundNewRange,NumSamples,1);
end