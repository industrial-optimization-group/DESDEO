# Test problems

## The four bar truss design problem (RE21)

The four bar truss design problem [1] has, as its two objective funtions, structural volume and joint displacement, and areas of member cross-sections as the four decision variables. The decision variables are constrained has four constraints related to member stresses. The variables are continuous and the problem's Pareto front is convex.

The objective functions and constraints for the four bar truss design problem are defined as follows:

$$\min_{\mathbf{x}}  f_1(\mathbf{x})  = L(2x_1 + \sqrt{2}x_2 + \sqrt{x_3} + x_4)$$
$$\min_{\mathbf{x}}  f_2(\mathbf{x})  = \frac{FL}{E}\left(\frac{2}{x_1} + \frac{2\sqrt{2}}{x_2} - \frac{2\sqrt{2}}{x_3} + \frac{2}{x_4}\right) $$
$$\text{s.t.,}    \frac{F}{\sigma} \leq x_1  \leq 3\frac{F}{\sigma},$$
$$\sqrt{2}\frac{F}{\sigma} \leq x_2  \leq 3\frac{F}{\sigma},$$
$$\sqrt{2}\frac{F}{\sigma} \leq x_3  \leq 3\frac{F}{\sigma},$$
$$\frac{F}{\sigma} \leq x_4  \leq 3\frac{F}{\sigma},$$

where $F = 10$ $kN$, $E = 2e^5$ $kN/cm^2$, $L = 200$ $cm$, and $\sigma = 10$ $kN/cm^2$.

## References
[1]: Cheng, F. Y., & Li, X. S. (1999). Generalized center method for multiobjective engineering optimization. Engineering Optimization, 31(5), 641-661.