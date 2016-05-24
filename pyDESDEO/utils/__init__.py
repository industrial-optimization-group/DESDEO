import numpy as np

def reachable_points(points,lower,upper):
    points=np.array(points)
    # There is faster way to do this
    points=points[np.all(points<np.array(upper),axis=1)]
    points=points[np.all(points>np.array(lower),axis=1)]
    return points