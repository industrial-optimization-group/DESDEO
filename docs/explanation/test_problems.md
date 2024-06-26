# Test problems

In DESDEO, some known test problem have been implemented and may be used to test the framework and the optimization methods implemented in it.
Here, some of those test problems are introduced and described.

## The four bar truss design problem (RE21)

The four bar truss design problem [1] has, as its two objective funtions, structural volume and joint displacement, and areas of member cross-sections as the four decision variables. The decision variables are constrained has four constraints related to member stresses. The variables are continuous and the problem's Pareto front is convex.

The objective functions and constraints for the four bar truss design problem are defined as follows:

$$\begin{align}
    &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = L(2x_1 + \sqrt{2}x_2 + \sqrt{x_3} + x_4) \\
    & & f_2(\mathbf{x}) & = \frac{FL}{E}\left(\frac{2}{x_1} + \frac{2\sqrt{2}}{x_2}
    - \frac{2\sqrt{2}}{x_3} + \frac{2}{x_4}\right) \\
    &\text{s.t.,}   & \frac{F}{\sigma} \leq x_1 & \leq 3\frac{F}{\sigma},\\
    & & \sqrt{2}\frac{F}{\sigma} \leq x_2 & \leq 3\frac{F}{\sigma},\\
    & & \sqrt{2}\frac{F}{\sigma} \leq x_3 & \leq 3\frac{F}{\sigma},\\
    & & \frac{F}{\sigma} \leq x_4 & \leq 3\frac{F}{\sigma},\\
\end{align}$$

where $x_1, x_4 \in [a, 3a]$, $x_2, x_3 \in [\sqrt{2}a, 3a]$, and $a = F/\sigma$. The parameters are defined as $F = 10$ $kN$, $E = 2e^5$ $kN/cm^2$, $L = 200$ $cm$, and $\sigma = 10$ $kN/cm^2$.

Here is an approximation of the four bar truss design problem's Pareto front:

## The reinforced concrete beam design problem (RE22)

In the reinforced concrete beam design problem [3], the first objective is to minimize the total cost of concrete and reinforcing steel of the beam. The second objective is to minimize the sum of the two constraint violations. The decision variable $x_1$ has a predefined discrete value[^1] from 0.2 to 15. That makes the decision variables a mix of continuous and discrete variables.

The objective functions and constraints for the reinforced concrete beam design problem are defined as follows:

$$\begin{align}
    &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 29.4x_1 + 0.6x_2x_3 \\
    & & f_2(\mathbf{x}) & = \sum_{i=1}^2 \max\{g_i(\mathbf{x}), 0\} \\
    &\text{s.t.,}   & g_1(\mathbf{x}) & = x_1x_3 - 7.735\frac{x_1^2}{x_2} - 180 \geq 0,\\
    & & g_2(\mathbf{x}) & = 4 - \frac{x_3}{x_2} \geq 0,
\end{align}$$

where $x_2 \in [0,20]$ and $x_3 \in [0,40].$

Here is an approximation of the reinforced concrete beam design problem's Pareto front:

## The pressure vessel design problem (RE23)

The pressure vessel design problem [4] involves a cylindrical pressure vessel that is capped at both ends by hemispherical heads. The first objective is to minimize the total cost, including the cost of material, forming and welding. The second objective is to minimize the sum of the three constraint violations. The decision variables $x_1$ and $x_2$ represent the thickness of the shell and the head, and the decision variables $x_3$ and $x_4$ represent the inner radius and length of the cylindrical section. The units for each decision variable are inches. The decision variables $x_1$ and $x_2$ are integer multiples of 0.0625 inches, which is the available thickness of rolled steel plates. That makes the decision variables a mix of continuous and discrete variables. The Pareto front for the problem is disconnected.

The objective functions and constraints for the reinforced concrete beam design problem are defined as follows:

$$\begin{align}
    &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = 0.6224x_1x_3x_4 + 1.7781x_2x_3^2 + 3.1661x_1^2x_4 + 19.84x_1^2x_3 \\
    & & f_2(\mathbf{x}) & = \sum_{i=1}^3 \max\{g_i(\mathbf{x}), 0\} \\
    &\text{s.t.,}   & g_1(\mathbf{x}) & = -x_1 + 0.0193x_3 \leq 0,\\
    & & g_2(\mathbf{x}) & = -x_2 + 0.00954x_3 \leq 0, \\
    & & g_3(\mathbf{x}) & = -\pi x_3^2x_4 - \frac{4}{3}\pi x_3^3 + 1\ 296\ 000 \leq 0.
\end{align}$$

Here is an approximation of the pressure vessel design problem's Pareto front:

## The hatch cover design problem (RE24)

In the hatch cover design problem [3], the first objective is to minimize the weight of the hatch cover. The second objective is to minimize the sum of the four constraint violations. The two decision variables $x_1$ and $x_2$ represent the flange thickness and the beam height of the hatch cover. Both decision variables are continuous and the Pareto front for the problem is convex.

The objective functions and constraints for the hatch cover design problem are defined as follows:

$$\begin{align}
    &\min_{\mathbf{x}} & f_1(\mathbf{x}) & = x_1 + 120x_2 \\
    & & f_2(\mathbf{x}) & = \sum_{i=1}^4 \max\{g_i(\mathbf{x}), 0\} \\
    &\text{s.t.,}   & g_1(\mathbf{x}) & = 1.0 - \frac{\sigma_b}{\sigma_{b,max}} \geq 0,\\
    & & g_2(\mathbf{x}) & = 1.0 - \frac{\tau}{\tau_{max}} \geq 0, \\
    & & g_3(\mathbf{x}) & = 1.0 - \frac{\delta}{\delta_{max}} \geq 0, \\
    & & g_4(\mathbf{x}) & = 1.0 - \frac{\sigma_b}{\sigma_{k}} \geq 0,
\end{align}$$

where $x_1 \in [0.5, 4]$ and $x_2 \in [4, 50]$. The parameters are defined as $\sigma_{b,max} = 700 kg/cm^2$, $\tau_{max} = 450 kg/cm$, $\delta_{max} = 1.5 cm$, $\sigma_k = Ex_1^2/100 kg/cm^2$, $\sigma_b = 4500/(x_1x_2) kg/cm^2$, $\tau = 1800/x_2 kg/cm^2$, $\delta = 56.2 \times 10^4/(Ex_1x_2^2)$, and $E = 700\ 000 kg/cm^2$.

Here is an approximation of the hatch cover design problem's Pareto front:

## References
[1]: Cheng, F. Y., & Li, X. S. (1999). Generalized center method for multiobjective engineering optimization. Engineering Optimization, 31(5), 641-661.

[2]: Tanabe, R. & Ishibuchi, H. (2020). An easy-to-use real-world multi-objective optimization problem suite. Applied soft computing, 89, 106078. https://doi.org/10.1016/j.asoc.2020.106078.

[3]: Amir, H. M., & Hasegawa, T. (1989). Nonlinear mixed-discrete structural optimization. Journal of Structural Engineering, 115(3), 626-646.

[4]: Kannan, B. K., & Kramer, S. N. (1994). An augmented Lagrange multiplier based method for mixed integer discrete continuous optimization and its applications to mechanical design.

[^1]: A set of predefined discrete values for the first decision variable: {0.2, 0.31, 0.4, 0.44, 0.6, 0.62, 0.79, 0.8, 0.88, 0.93, 1, 1.2, 1.24, 1.32, 1.4, 1.55, 1.58, 1.6, 1.76, 1.8, 1.86, 2, 2.17, 2.2, 2.37, 2.4, 2.48, 2.6, 2.64, 2.79, 2.8, 3, 3.08, 3, 1, 3.16, 3.41, 3.52, 3.6, 3.72, 3.95, 3.96, 4, 4.03, 4.2, 4.34, 4.4, 4.65, 4.74, 4.8, 4.84, 5, 5.28, 5.4, 5.53, 5.72, 6, 6.16, 6.32, 6.6, 7.11, 7.2, 7.8, 7.9, 8, 8.4, 8.69, 9, 9.48, 10.27, 11, 11.06, 11.85, 12, 13, 14, 15}.
