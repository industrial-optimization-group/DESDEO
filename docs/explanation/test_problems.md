# Test problems

In DESDEO, some known test problem have been implemented and may be used to test the framework and the optimization methods implemented in it.
Here, some of those test problems are introduced and described.

## The four bar truss design problem (RE21)

The four bar truss design problem [1] has, as its two objective funtions, structural volume and joint displacement, and areas of member cross-sections as the four decision variables. The decision variables are constrained has four constraints related to member stresses. The variables are continuous and the problem's Pareto front is convex.

The objective functions and constraints for the four bar truss design problem are defined as follows:

$$\begin{align}
    &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = L(2x_1 + \sqrt{2}x_2 + \sqrt{x_3} + x_4) \\
    &\min_{\mathbf{x}} & f_2(\mathbf{x}) & = \frac{FL}{E}\left(\frac{2}{x_1} + \frac{2\sqrt{2}}{x_2}
    - \frac{2\sqrt{2}}{x_3} + \frac{2}{x_4}\right) \\
    &\text{s.t.,}   & \frac{F}{\sigma} \leq x_1 & \leq 3\frac{F}{\sigma},\\
    & & \sqrt{2}\frac{F}{\sigma} \leq x_2 & \leq 3\frac{F}{\sigma},\\
    & & \sqrt{2}\frac{F}{\sigma} \leq x_3 & \leq 3\frac{F}{\sigma},\\
    & & \frac{F}{\sigma} \leq x_4 & \leq 3\frac{F}{\sigma}.\\
\end{align}$$

where $F = 10$ $kN$, $E = 2e^5$ $kN/cm^2$, $L = 200$ $cm$, and $\sigma = 10$ $kN/cm^2$.

Here is an approximation of the four bar truss design problem's Pareto front (taken from [2]), where the $x$ and $y$ axes represent the values of the objective functions $f_1$ and $f_2$ respectively:

<img src="../assets/re21_pf_ss.png" alt="A picture of the Pareto front" width="400"/>

## References
[1]: Cheng, F. Y., & Li, X. S. (1999). Generalized center method for multiobjective engineering optimization. Engineering Optimization, 31(5), 641-661.

[2]: Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective optimization problem suite. Applied soft computing, 89, 106078. https://doi.org/10.1016/j.asoc.2020.106078.