r"""The General Aviation Aircraft (GAA) product family design problem.

A family of three light aircraft -- a 2-, 4- and 6-seat variant -- is designed together. Each variant
has its own nine design variables, so the problem has 27 continuous variables, and each variant's nine
performance responses come from a second-order polynomial response surface fitted to a conceptual
design code. The ten objectives aggregate those responses across the family, and the single constraint
is the total violation of eighteen performance limits.

The problem is the only closed-form, deterministic, many-objective real-world problem in common use:
there are no data files, no simulator and no random draws, and it reaches ten objectives, where the
rest of the real-world literature stops at six.

Provenance:
    The response surface coefficients were extracted mechanically from the MOEA Framework's `GAA.java`,
    which carries an MIT-style grant from Timothy W. Simpson and others, and were checked against that
    implementation's own unit test: both corners of the design box reproduce all ten objectives and the
    constraint exactly, to the last bit. See `tests/test_testproblems.py`.

References:
    Simpson, T. W., Chen, W., Allen, J. K., & Mistree, F. (1996). Conceptual design of a family of
        products through the use of the robust concept exploration method. 6th AIAA/USAF/NASA/ISSMO
        Symposium on Multidisciplinary Analysis and Optimization, 2, 1535-1545.
        https://doi.org/10.2514/6.1996-4161.

    Simpson, T. W., & D'Souza, B. S. (2004). Assessing variable levels of platform commonality within
        a product family using a multiobjective genetic algorithm. Concurrent Engineering, 12(2),
        119-129. https://doi.org/10.1177/1063293X04044383.

    Woodruff, M. J., Reed, P. M., & Simpson, T. W. (2013). Many objective visual analytics: rethinking
        the design of complex engineered systems. Structural and Multidisciplinary Optimization, 48(1),
        201-219. https://doi.org/10.1007/s00158-013-0891-z.

    Hadka, D., Reed, P. M., & Simpson, T. W. (2012). Diagnostic assessment of the borg MOEA for
        many-objective product family design problems. IEEE Congress on Evolutionary Computation,
        986-995. https://doi.org/10.1109/CEC.2012.6256466.
"""

from desdeo.problem.schema import (
    Constraint,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

_SEATS = (2, 4, 6)
"""The three aircraft in the family, by seat count."""

# The nine design variables of one aircraft, in the order the response surfaces expect them. Each is
# scaled to [-1, 1] before entering a surface, by subtracting the centre and dividing by the half
# range; the design box is exactly centre +/- half range, so the bounds are not stated separately.
_DESIGN = (
    ("cspd", "cruise speed", 0.36, 0.12),
    ("ar", "aspect ratio", 9.0, 2.0),
    ("sweep", "wing sweep", 3.0, 3.0),
    ("dprop", "propeller diameter", 5.734, 0.234),
    ("wingld", "wing loading", 22.0, 3.0),
    ("af", "propeller activity factor", 97.5, 12.5),
    ("seatw", "seat width", 17.0, 3.0),
    ("elodt", "tail length to diameter ratio", 3.375, 0.375),
    ("taper", "taper ratio", 0.73, 0.27),
)

# The nine responses of one aircraft. The first six are minimised across the family and the last three
# are maximised; the tenth objective is the product family penalty function, which has no per-aircraft
# response behind it.
_RESPONSES = (
    ("noise", "flyover noise", False),
    ("wemp", "empty weight", False),
    ("doc", "direct operating cost", False),
    ("rough", "ride roughness", False),
    ("wfuel", "fuel weight", False),
    ("purch", "purchase price", False),
    ("range", "range", True),
    ("ldmax", "maximum lift to drag ratio", True),
    ("vcmax", "maximum cruise speed", True),
)

# Performance limits behind the constraint, per aircraft. Every response but the fuel weight has the
# same limit for all three variants. A range below its limit is a violation; the others violate above.
_CONSTRAINT_LIMITS = {
    "noise": {2: 75.0, 4: 75.0, 6: 75.0},
    "wemp": {2: 2200.0, 4: 2200.0, 6: 2200.0},
    "doc": {2: 80.0, 4: 80.0, 6: 80.0},
    "rough": {2: 2.0, 4: 2.0, 6: 2.0},
    "wfuel": {2: 450.0, 4: 475.0, 6: 500.0},
    "range": {2: 2000.0, 4: 2000.0, 6: 2000.0},
}

# The order of the coefficients in _SURFACE_COEFFICIENTS: the constant, then the nine linear terms,
# then the thirty-six pairwise interactions in index order, then the nine squares. A term is a tuple of
# indices into _DESIGN.
_TERMS: tuple[tuple[int, ...], ...] = (
    (),
    *((i,) for i in range(9)),
    *((i, j) for i in range(9) for j in range(i + 1, 9)),
    *((i, i) for i in range(9)),
)

# fmt: off
# The table is laid out five coefficients to a line to stay readable; the formatter would put
# each of the 1485 on its own.
_SURFACE_COEFFICIENTS: dict[tuple[str, int], tuple[float, ...]] = {
    ("noise", 2): (
        74.099998, -0.0004, -0.0156, 0.0003, 0.9684,
        0.0316, -0.0053, -0.0015, -0.0002, 0.0007,
        0.0, 0.0, -0.0001, -0.0001, -0.0001,
        0.0, 0.0001, 0.0, 0.0, -0.0012,
        -0.0014, -0.0002, 0.0, 0.0003, 0.0001,
        0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, -0.0003, 0.0058, -0.0001, 0.0002,
        -0.0001, 0.0002, -0.0003, -0.0002, 0.0001,
        -0.0001, 0.0, 0.0, -0.0001, -0.0001,
        0.0, 0.0008, 0.0016, 0.0011, 0.1105,
        0.0004, -0.0019, 0.0009, 0.001, 0.0007,
    ),
    ("noise", 4): (
        74.099998, -0.0005, -0.0158, 0.0003, 0.9682,
        0.0316, -0.0053, -0.0014, -0.0003, 0.0008,
        0.0, 0.0, -0.0001, -0.0001, -0.0001,
        0.0, 0.0001, 0.0, 0.0, -0.0012,
        -0.0014, -0.0002, 0.0, 0.0002, 0.0002,
        0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, -0.0003, 0.0057, -0.0001, 0.0001,
        0.0, 0.0002, -0.0002, -0.0001, 0.0001,
        -0.0001, 0.0, 0.0, -0.0001, 0.0,
        0.0, 0.0008, 0.0016, 0.0011, 0.1104,
        0.0003, -0.0019, 0.001, 0.001, 0.0007,
    ),
    ("noise", 6): (
        74.099998, -0.0004, -0.0156, 0.0003, 0.9682,
        0.0314, -0.0053, -0.0015, -0.0004, 0.0007,
        0.0, 0.0, -0.0001, -0.0001, -0.0001,
        0.0, 0.0, 0.0, 0.0, -0.0013,
        -0.0014, -0.0002, -0.0001, 0.0002, 0.0002,
        0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, -0.0003, 0.0057, -0.0002, 0.0001,
        -0.0001, 0.0002, -0.0002, -0.0002, 0.0001,
        -0.0001, 0.0, 0.0, -0.0001, 0.0,
        0.0, 0.0006, 0.0017, 0.0011, 0.1103,
        0.0004, -0.0021, 0.001, 0.001, 0.0008,
    ),
    ("wemp", 2): (
        1917, 5.979, 35.130001, -0.7119, 11.11,
        -32.290001, 5.739, 48.110001, 0.3376, 15.28,
        1.244, -0.1315, 1.129, -2.393, 0.3954,
        -0.4978, -0.3882, 0.5742, -0.2236, -0.0739,
        -3.805, -0.0164, -0.0923, -0.9326, 3.135,
        -0.0385, 0.4376, 0.0259, 0.4009, 0.3002,
        0.7036, -0.2083, 1.165, -0.2119, -0.1934,
        0.1462, -0.0644, 3.194, 2.672, -0.4407,
        -0.057, -0.0529, 0.0341, 4.88, 1.349,
        0.8836, 0.958, -1.812, 1.173, 0.753,
        3.638, 0.133, 5.323, 1.478, -0.192,
    ),
    ("wemp", 4): (
        1947, 6.338, 33.869999, -0.448, 11,
        -30.85, 5.723, 53.220001, 1.896, 15.26,
        1.963, -0.1599, 1.073, -1.699, 0.462,
        -0.9528, -0.9851, 0.5956, 0.0065, 0.0874,
        -3.447, 0.1024, -0.1814, 0.7878, 1.592,
        0.0288, 0.3498, 0.034, 0.3134, 0.2289,
        0.5603, -0.1862, 1.061, -0.0774, -0.2335,
        0.1385, -0.0914, 1.932, 1.853, -0.8019,
        -0.0754, -0.1306, 0.1086, 4.81, 1.309,
        1.265, 0.4046, 1.065, 0.7346, 0.4896,
        5.815, -0.1304, 3.595, 0.6296, 1.26,
    ),
    ("wemp", 6): (
        1972, 5.386, 33.290001, -0.0222, 10.82,
        -28.889999, 5.588, 61.32, 4.65, 16.620001,
        1.32, -0.2549, 0.9089, -1.403, 0.3601,
        -0.0118, 0.0123, 0.4761, 0.0455, -0.0596,
        -3.818, -0.0408, 0.5044, 0.2867, 2.497,
        0.0011, 0.151, 0.0524, 0.1164, 0.0491,
        0.391, 0.1823, 1.254, 0.0491, 0.1011,
        0.0538, 0.098, 1.807, 1.119, -1.437,
        0.0664, 0.0566, 0.0508, 2.914, 0.0969,
        -0.1483, 1.446, -2.524, 1.646, 1.381,
        2.651, 0.7561, 3.116, 1.211, -0.4489,
    ),
    ("doc", 2): (
        83.17, 12.53, -0.0477, -0.0215, 3.597,
        -0.7367, 0.7481, 0.733, -0.2029, 0.0393,
        0.6526, 0.0481, 1.208, 0.6802, 0.0992,
        -0.7074, 0.2768, 0.0109, 0.0031, 0.2146,
        -0.0721, -0.2445, -0.0172, 0.0127, 0.0087,
        0.0169, 0.0151, -0.0063, -0.0001, -0.0042,
        -0.0059, 0.0789, 0.676, -0.1912, 0.0519,
        -0.0265, 0.0136, 0.0804, 0.0577, 0.017,
        -0.0617, 0.0058, -0.0178, 0.0901, 0.0047,
        -0.003, -11.37, -0.2836, -0.3149, 5.337,
        -0.3711, -0.071, -0.2177, -0.2354, -0.238,
    ),
    ("doc", 4): (
        83.150002, 12.02, -0.072, -0.0126, 3.428,
        -0.704, 0.7248, 0.7224, -0.1421, 0.0407,
        0.613, 0.046, 1.155, 0.7144, 0.0944,
        -0.8399, 0.2251, 0.0082, 0.0082, 0.1826,
        -0.0606, -0.2352, -0.0486, 0.0162, 0.0211,
        0.0199, 0.0088, -0.0152, 0.0082, -0.0123,
        -0.0142, 0.1207, 0.6576, -0.2728, 0.0435,
        -0.0326, 0.0196, 0.0952, 0.0351, 0.0091,
        -0.0628, -0.0201, -0.0244, 0.0651, 0.0048,
        -0.0042, -10.95, -0.2401, -0.2203, 5.223,
        -0.2669, -0.0884, -0.2169, -0.306, -0.2231,
    ),
    ("doc", 6): (
        83.260002, 11.86, -0.0805, -0.0218, 3.345,
        -0.6443, 0.7039, 0.8256, -0.0905, 0.0305,
        0.6, 0.0284, 1.109, 0.6928, 0.0795,
        -0.9926, 0.1119, -0.0183, 0.0018, 0.1731,
        -0.0631, -0.246, -0.0581, -0.0008, -0.0048,
        0.0024, 0.0011, -0.0043, 0.0048, -0.0019,
        0.0025, 0.1331, 0.6487, -0.353, -0.0025,
        -0.0586, 0.005, 0.1121, 0.0345, 0.0103,
        -0.0674, 0.0003, -0.0133, 0.0316, -0.0007,
        0.0063, -10.77, -0.288, -0.288, 5.182,
        -0.2313, -0.0895, -0.2136, -0.2562, -0.2686,
    ),
    ("rough", 2): (
        2.197, -0.0002, 0.1541, -0.0012, 0.0222,
        -0.1611, -0.0012, -0.0628, -0.011, 0.0068,
        0.0006, 0.0001, 0.0, 0.001, 0.0,
        0.0001, -0.0002, -0.0006, -0.0001, 0.0006,
        -0.0113, -0.0001, -0.0045, -0.0017, -0.0011,
        -0.0002, -0.0004, 0.0, -0.0006, -0.0003,
        -0.0001, -0.0051, -0.0038, 0.0022, -0.0012,
        -0.0002, -0.001, -0.0036, -0.0025, -0.0025,
        0.0008, -0.0003, -0.0001, -0.001, -0.0007,
        0.0, 0.0012, -0.0273, -0.0048, 0.0033,
        0.0062, 0.0021, -0.0016, -0.0011, -0.0048,
    ),
    ("rough", 4): (
        2.191, -0.0001, 0.1584, -0.0017, 0.0238,
        -0.1632, -0.0008, -0.0666, -0.0142, 0.0069,
        -0.0002, 0.0001, 0.0, 0.0001, -0.0002,
        0.0008, 0.0005, -0.0007, -0.0003, 0.0006,
        -0.012, -0.0003, -0.0051, -0.0037, 0.0007,
        -0.0002, -0.0003, -0.0001, -0.0004, -0.0002,
        -0.0001, -0.005, -0.0037, 0.0022, -0.0008,
        -0.0003, -0.0008, -0.0018, -0.0012, -0.0021,
        0.0009, -0.0001, -0.0002, -0.0011, -0.0012,
        -0.0008, -0.0001, -0.0302, -0.0015, 0.0041,
        0.005, 0.0029, 0.0009, -0.0007, -0.0058,
    ),
    ("rough", 6): (
        2.161, 0.0007, 0.156, -0.0022, 0.0239,
        -0.1649, -0.0007, -0.0675, -0.0135, 0.0056,
        0.0006, 0.0001, 0.0001, 0.0, 0.0,
        0.0, -0.0003, -0.0003, -0.0003, 0.0008,
        -0.0119, 0.0, -0.0054, -0.0026, -0.0003,
        -0.0002, -0.0002, -0.0001, -0.0002, -0.0002,
        0.0001, -0.0051, -0.0038, 0.0024, -0.0009,
        -0.0002, -0.001, -0.0018, -0.0009, -0.0017,
        0.0009, -0.0002, -0.0001, -0.0005, -0.0001,
        0.0003, -0.0006, -0.0255, -0.0043, 0.0039,
        0.0092, 0.0014, 0.0003, -0.0007, -0.0052,
    ),
    ("wfuel", 2): (
        416.399994, -6.093, -31.91, 0.7968, -19.17,
        34.189999, -7.57, -49.610001, 0.2331, -15.33,
        -1.201, 0.1735, -1.247, 1.703, -0.4588,
        0.1585, 0.6156, -0.528, 0.2215, -0.4976,
        4.058, -0.108, 0.2679, 0.8514, -3.182,
        0.0359, -0.482, -0.0207, -0.3878, -0.3249,
        -0.715, 0.3374, -2.403, 0.4519, 0.1352,
        -0.123, 0.2498, -2.896, -3.016, 0.3662,
        -0.114, 0.0571, -0.0222, -4.689, -1.339,
        -0.9311, -0.7538, 1.13, -1.078, -5.989,
        -3.043, 0.0627, -4.958, -1.41, 0.3532,
    ),
    ("wfuel", 4): (
        385.5, -6.707, -30.57, 0.5048, -18.91,
        33.009998, -7.543, -55.169998, -1.447, -15.32,
        -1.938, 0.18, -1.201, 1.434, -0.5591,
        0.272, 1.172, -0.5566, -0.0178, -0.6466,
        3.714, -0.1913, 0.3522, -0.828, -1.633,
        -0.0415, -0.3772, -0.0287, -0.3237, -0.2653,
        -0.5519, 0.5867, -2.332, 0.0168, 0.2074,
        -0.1206, 0.3465, -1.509, -2.134, 0.7418,
        -0.0803, 0.1825, -0.1052, -4.86, -1.355,
        -1.289, 0.1451, -1.698, -0.6064, -6.025,
        -4.978, 0.2611, -3.229, -0.4999, -1.068,
    ),
    ("wfuel", 6): (
        359.700012, -5.78, -29.99, 0.0682, -18.709999,
        31, -7.332, -63.599998, -4.44, -16.709999,
        -1.317, 0.2715, -1.069, 1.185, -0.3931,
        -0.8091, 0.0543, -0.448, -0.0418, -0.5179,
        4.113, -0.0407, -0.3222, -0.3059, -2.526,
        -0.0077, -0.1761, -0.0543, -0.1319, -0.0633,
        -0.3999, 0.2791, -2.456, -0.1367, -0.155,
        -0.0405, 0.0736, -1.298, -1.258, 1.389,
        -0.1952, -0.0011, -0.0391, -2.965, -0.1262,
        0.1433, -0.8956, 1.729, -1.613, -6.309,
        -1.949, -0.6581, -2.723, -1.181, 0.5244,
    ),
    ("purch", 2): (
        43280, 133.1, 780.400024, -1.501, 494,
        -331.8, 191.2, 786, 102, 333.9,
        25.95, -2.442, 28.280001, -50.509998, 11.55,
        -6.188, -4.326, 13.78, -3.335, 0.4272,
        -69.110001, -0.8834, 7.221, -20.389999, 69.580002,
        -1.107, 7.078, 0.0705, 5.359, 4.936,
        14.77, -21.82, 22.17, 14.2, -7.537,
        5.813, -6.771, 27.99, 47.080002, -9.888,
        3.135, -2.658, 1.033, 82.230003, 27.969999,
        16.110001, 10.51, -49.189999, 26.51, 35.310001,
        33.560001, 10.66, 74.309998, 8.461, -0.7392,
    ),
    ("purch", 4): (
        43730, 142.5, 756.5, 2.004, 504.799988,
        -314.799988, 194.100006, 890.5, 114.099998, 334.5,
        43.029999, -2.865, 27.42, -35.060001, 13.28,
        -17.02, -18.83, 14.26, 0.8277, 3.724,
        -60.380001, 3.039, 7.395, 18.809999, 35.360001,
        -0.0758, 6.451, 0.5043, 4.745, 3.97,
        11.97, -20.6, 20.549999, 18.09, -7.554,
        5.429, -8.093, 2.433, 29.82, -17.860001,
        3.676, -3.442, 2.995, 86.110001, 29.129999,
        26.49, -1.456, 16.049999, -0.7055, 45.990002,
        87.14, 0.8945, 51.650002, -2.256, 25.59,
    ),
    ("purch", 6): (
        44220, 124.400002, 749.200012, 9.32, 506.899994,
        -290.600006, 192.800003, 1034, 144.5, 364.799988,
        27.370001, -5.918, 24.51, -29.690001, 10.97,
        2.652, 2.262, 11.44, 2.046, 0.2715,
        -67.760002, -0.3336, 25.07, 7.377, 56.369999,
        -0.1879, 1.594, 1.086, 1.375, 0.4313,
        8.3, -11.7, 24.440001, 23.85, 1.195,
        3.797, -3.027, 4.452, 18.059999, -30.709999,
        7.103, 1.01, 1.463, 53.560001, 4.063,
        -3.483, 15.24, -71.910004, 33.990002, 60.540001,
        15.24, 28.49, 50.490002, 18.190001, -9.011,
    ),
    ("range", 2): (
        1971, -6.807, -76.230003, 2.885, -363.799988,
        -383.100006, -68.099998, -67.480003, 18.09, -165.699997,
        0.084, 0.2793, 1.674, 3.342, 0.1543,
        -0.4629, 0.8574, 2.537, 0.0098, -23.23,
        -25.799999, -1.787, 9.432, -1.912, -40.200001,
        -1.479, -1.311, -0.2168, -0.7168, -0.584,
        -0.8652, 121.099998, -26.709999, 25.280001, -10.74,
        37.080002, 21.290001, 19.299999, -4.318, -20.360001,
        3.611, -1.678, 7.541, -7.232, 16.860001,
        -3.006, -11.61, 4.892, -11.61, -84.110001,
        65.389999, -7.108, -15.61, -13.11, 8.892,
    ),
    ("range", 4): (
        1941, -6.768, -68.910004, 2.315, -346.799988,
        -365, -65.25, -77.599998, 13.19, -155.300003,
        0.1113, 0.2207, 1.229, 3.721, 0.0176,
        -0.0527, 0.6777, 2.674, 0.0762, -24.07,
        -31.309999, -1.979, 11.8, -0.623, -38.310001,
        -1.15, -0.9785, -0.2051, -0.5879, -0.4512,
        -0.7754, 115.400002, -26.84, 27.91, -7.897,
        34.349998, 20.610001, 28.92, -3.006, -27.870001,
        4.107, -1.17, 7.186, -7.389, 18.02,
        -2.451, -12.83, 4.667, -12.33, -85.330002,
        57.169998, -8.833, -16.33, -13.33, 8.167,
    ),
    ("range", 6): (
        1932, -6.389, -64.400002, 1.778, -342.799988,
        -356.399994, -64.639999, -91.739998, 5.658, -150.5,
        -0.2363, 0.0566, 1.346, 3.529, 0.0215,
        -0.291, 0.0293, 2.416, 0.0449, -24.780001,
        -35.150002, -2.131, 13.65, -0.0059, -35.599998,
        -0.9512, -0.6113, -0.166, -0.3457, -0.1191,
        -0.5762, 114.300003, -26.83, 33.290001, -4.76,
        33.189999, 20.6, 38.630001, 0.4238, -31.940001,
        5.057, -0.8809, 6.873, -3.928, 20.360001,
        0.0918, -11.73, 4.268, -10.73, -83.730003,
        39.27, -7.232, -14.23, -11.73, 9.268,
    ),
    ("ldmax", 2): (
        17.780001, 0.4845, 1.625, 0.0267, -0.0153,
        -0.5289, -0.007, -0.4965, 0.2108, 0.0302,
        0.0598, 0.0019, -0.0085, -0.0146, -0.0018,
        -0.0014, 0.0104, 0.0044, 0.0053, -0.0024,
        -0.0612, -0.001, -0.0517, 0.0128, 0.0043,
        -0.0001, -0.0054, 0.0, -0.0072, -0.0039,
        0.0, 0.0002, -0.0012, 0.0016, -0.0001,
        0.0007, -0.0001, -0.0727, -0.0256, -0.0033,
        0.0008, -0.0003, 0.0003, -0.0525, -0.0071,
        -0.0059, -0.0897, -0.1488, -0.0116, -0.0009,
        0.0157, -0.001, -0.0577, -0.0305, -0.0009,
    ),
    ("ldmax", 4): (
        17.43, 0.4811, 1.584, 0.0212, -0.0128,
        -0.5456, -0.0054, -0.4984, 0.1607, 0.0288,
        0.0635, 0.0013, -0.0078, -0.0123, -0.0011,
        -0.0065, 0.0049, 0.0038, 0.0038, -0.0014,
        -0.0601, -0.0003, -0.0503, 0.017, -0.0029,
        0.0002, -0.0032, 0.0001, -0.0043, -0.0021,
        -0.0001, -0.0007, -0.0015, 0.0009, -0.0002,
        0.0008, -0.0008, -0.0682, -0.0243, -0.0047,
        0.0, -0.0004, 0.0007, -0.0406, -0.0052,
        -0.0018, -0.0923, -0.1312, -0.0127, -0.0041,
        0.0304, -0.0044, -0.0545, -0.0239, 0.0066,
    ),
    ("ldmax", 6): (
        17.34, 0.4817, 1.573, 0.0179, -0.0117,
        -0.5804, -0.0053, -0.5638, 0.0986, 0.0278,
        0.0603, 0.0004, -0.0074, -0.0132, -0.0014,
        -0.0059, 0.0053, 0.0024, 0.0032, -0.0021,
        -0.0632, -0.0009, -0.0553, 0.0072, 0.0011,
        0.0002, -0.0028, 0.0, -0.0035, -0.0016,
        -0.0006, 0.0003, -0.0006, 0.0014, 0.001,
        0.0004, -0.0001, -0.0563, -0.0173, -0.0049,
        0.0006, 0.0004, 0.0001, -0.0254, -0.0069,
        -0.0037, -0.0838, -0.1499, -0.0058, 0.0016,
        0.0214, 0.0013, -0.0337, -0.0133, 0.0028,
    ),
    ("vcmax", 2): (
        200.4, -0.3799, 0.8236, 0.2168, 1.74,
        5.589, -0.1683, -3.522, 1.559, 0.2442,
        -0.0215, 0.0054, -0.0465, -0.0144, -0.0069,
        0.0578, 0.0557, 0.0221, 0.0175, -0.0942,
        0.1402, -0.0079, 0.0147, -0.071, -0.0104,
        -0.0067, -0.0306, -0.0078, -0.0534, -0.0224,
        0.0026, -0.2771, -0.3476, 0.2093, -0.0864,
        -0.0051, -0.0948, -0.7081, -0.1219, -0.016,
        0.0555, -0.0342, -0.0049, -0.3658, -0.046,
        -0.0504, -0.1452, -0.2937, 0.0303, 0.1378,
        -0.6522, 0.1378, -0.6102, -0.3722, 0.0303,
    ),
    ("vcmax", 4): (
        197.800003, -0.3562, 0.7729, 0.1807, 1.886,
        5.332, -0.1262, -3.585, 1.18, 0.2323,
        0.0123, 0.0073, -0.0462, 0.0075, -0.003,
        0.0375, 0.0225, 0.017, 0.0071, -0.0914,
        0.1716, -0.0115, 0.0278, -0.0074, -0.0583,
        -0.0124, -0.0116, -0.0041, -0.0337, -0.0132,
        0.0028, -0.2578, -0.3341, 0.2057, -0.0696,
        -0.0125, -0.1043, -0.6842, -0.1276, -0.0217,
        0.0663, -0.0185, 0.0001, -0.2758, -0.039,
        -0.0162, -0.1479, -0.1989, -0.2574, 0.3991,
        -0.5109, 0.0706, -0.4174, -0.2574, -0.0384,
    ),
    ("vcmax", 6): (
        197.100006, -0.3331, 0.7564, 0.153, 1.918,
        5.044, -0.1139, -4.07, 0.7276, 0.2242,
        -0.0231, -0.009, -0.0365, -0.0011, -0.0064,
        0.0355, 0.028, 0.013, 0.013, -0.0947,
        0.1791, -0.0178, 0.0598, -0.0216, -0.0274,
        -0.006, -0.0243, -0.001, -0.0233, -0.0108,
        -0.0011, -0.2368, -0.334, 0.2329, -0.0419,
        -0.0148, -0.0851, -0.6179, -0.0865, -0.0158,
        0.0691, -0.0088, -0.0056, -0.1699, -0.0462,
        -0.028, -0.2315, -0.384, -0.013, 0.315,
        -0.612, 0.206, -0.2825, -0.1225, -0.013,
    ),
}
# fmt: on


def _scaled_symbol(design: str, seats: int) -> str:
    return f"{design}_{seats}"


def _surface_expression(response: str, seats: int) -> str:
    """Write one response surface as a polynomial in that aircraft's nine scaled design variables."""
    coefficients = _SURFACE_COEFFICIENTS[(response, seats)]
    symbols = [_scaled_symbol(design, seats) for design, *_ in _DESIGN]

    terms = []
    for coefficient, term in zip(coefficients, _TERMS, strict=True):
        if coefficient == 0.0:
            # A fitted coefficient that rounded to zero contributes nothing and is left out, which
            # keeps the expression to the roughly fifty terms that actually matter.
            continue
        factors = [f"({coefficient!r})", *(symbols[i] for i in term)]
        terms.append(" * ".join(factors))

    return " + ".join(terms)


def gaa(*, fold_constraint: bool = False) -> Problem:
    r"""Defines the General Aviation Aircraft product family design problem.

    Three aircraft -- a 2-, 4- and 6-seat variant -- are designed as one family. Each has nine design
    variables, giving 27 in total, and nine performance responses predicted by second-order polynomial
    response surfaces in those variables. Writing $R_{r,s}$ for response $r$ of the $s$-seat aircraft,
    and $z_{i,s}$ for its $i$-th design variable scaled to $[-1, 1]$:

    \begin{align}
        &\min_{\mathbf{x}} & f_1 \ldots f_6 & = \max_{s \in \{2,4,6\}} R_{r,s},
            & r & \in \{\text{noise}, \text{wemp}, \text{doc}, \text{rough}, \text{wfuel},
            \text{purch}\} \\
        &\max_{\mathbf{x}} & f_7 \ldots f_9 & = \min_{s \in \{2,4,6\}} R_{r,s},
            & r & \in \{\text{range}, \text{ldmax}, \text{vcmax}\} \\
        &\min_{\mathbf{x}} & f_{10} & = \sqrt{\sum_{i=1}^{9}\sum_{s \in \{2,4,6\}}
            \left(z_{i,s} - \bar{z_i}\right)^2}
    \end{align}

    The tenth objective is the *product family penalty function*: the spread of the three aircraft
    around their common mean design. Driving it to zero makes the three variants identical, which is
    the cheapest family to build and the worst-performing one, so it trades against all nine
    performance objectives at once. That trade is what the problem exists to study.

    The constraint is the total violation of eighteen performance limits -- six responses on each of
    the three aircraft, each normalised by its limit and clamped at zero:

    \begin{align}
        g(\mathbf{x}) = \sum_{s \in \{2,4,6\}} \left(
            \sum_{r} \max\left\{\frac{R_{r,s} - L_{r,s}}{L_{r,s}}, 0\right\}
            + \max\left\{\frac{L_{\text{range},s} - R_{\text{range},s}}{L_{\text{range},s}}, 0\right\}
        \right) \leq 0
    \end{align}

    Every term is clamped at zero, so $g \geq 0$ always and a solution is feasible exactly when it
    meets all eighteen limits.

    Note:
        The three variants have **different** response surface coefficients -- 27 fitted surfaces in
        all, not 9 reused three times.

        The running maxima of the first six objectives start at 0 and the running minima of the next
        three start at 200 000, exactly as in the reference implementation. Those bounds never bind on
        the design box, but they are kept so that the two implementations agree bit for bit.

        The reference implementation also computes a set of `*_DEV` goal deviations that nothing then
        reads. They are dead code there and are not reproduced here.

    Args:
        fold_constraint (bool, optional): if `True`, return the constraint violation as an eleventh
            objective and no constraints, in the manner of the RE suite, which makes the problem
            bound-constrained. If `False`, return the ten objectives and the constraint as published.
            Defaults to `False`.

    Returns:
        Problem: an instance of the General Aviation Aircraft product family design problem.
    """
    variables = []
    extras = []

    for aircraft, seats in enumerate(_SEATS):
        for i, (design, description, centre, half_range) in enumerate(_DESIGN):
            symbol = f"x_{aircraft * len(_DESIGN) + i + 1}"
            variables.append(
                Variable(
                    name=f"{description} ({seats}-seat)",
                    symbol=symbol,
                    variable_type=VariableTypeEnum.real,
                    lowerbound=centre - half_range,
                    upperbound=centre + half_range,
                    initial_value=centre,
                )
            )
            extras.append(
                ExtraFunction(
                    name=f"scaled {design} ({seats}-seat)",
                    symbol=_scaled_symbol(design, seats),
                    func=f"({symbol} - {centre!r}) / {half_range!r}",
                    is_linear=True,
                    is_convex=True,
                    is_twice_differentiable=True,
                )
            )

    for response, description, _ in _RESPONSES:
        for seats in _SEATS:
            extras.append(
                ExtraFunction(
                    name=f"{description} ({seats}-seat)",
                    symbol=f"{response}_{seats}",
                    func=_surface_expression(response, seats),
                    is_linear=False,
                    is_convex=False,  # Not checked
                    is_twice_differentiable=True,
                )
            )

    objectives = []
    for index, (response, description, maximize) in enumerate(_RESPONSES, start=1):
        across = ", ".join(f"{response}_{seats}" for seats in _SEATS)
        # The starting value of the reference implementation's running extremum comes first.
        aggregate = f"Min(200000, {across})" if maximize else f"Max(0, {across})"
        objectives.append(
            Objective(
                # Both aggregations take the worst case: the largest of the six that are minimised,
                # the smallest of the three that are maximised.
                name=f"worst {description} across the family",
                symbol=f"f_{index}",
                func=aggregate,
                objective_type=ObjectiveTypeEnum.analytical,
                maximize=maximize,
                is_linear=False,
                is_convex=False,  # Not checked
                is_twice_differentiable=False,
            )
        )

    for design, description, _, _ in _DESIGN:
        across = " + ".join(_scaled_symbol(design, seats) for seats in _SEATS)
        extras.append(
            ExtraFunction(
                name=f"family mean of the scaled {description}",
                symbol=f"{design}_mean",
                func=f"({across}) / {len(_SEATS)}",
                is_linear=True,
                is_convex=True,
                is_twice_differentiable=True,
            )
        )

    spread = " + ".join(
        f"({_scaled_symbol(design, seats)} - {design}_mean)**2" for design, *_ in _DESIGN for seats in _SEATS
    )
    objectives.append(
        Objective(
            name="product family penalty function",
            symbol=f"f_{len(_RESPONSES) + 1}",
            func=f"Sqrt({spread})",
            objective_type=ObjectiveTypeEnum.analytical,
            is_linear=False,
            is_convex=False,  # Not checked
            is_twice_differentiable=False,
        )
    )

    violations = []
    for response, limits in _CONSTRAINT_LIMITS.items():
        for seats in _SEATS:
            limit = limits[seats]
            symbol = f"{response}_{seats}"
            # The range must exceed its limit; every other response must stay below it.
            excess = f"({limit!r} - {symbol})" if response == "range" else f"({symbol} - {limit!r})"
            violations.append(f"Max({excess} / {limit!r}, 0)")
    total_violation = " + ".join(violations)

    if fold_constraint:
        objectives.append(
            Objective(
                name="total performance limit violation",
                symbol=f"f_{len(_RESPONSES) + 2}",
                func=total_violation,
                objective_type=ObjectiveTypeEnum.analytical,
                is_linear=False,
                is_convex=False,  # Not checked
                is_twice_differentiable=False,
            )
        )
        constraints = None
    else:
        constraints = [
            Constraint(
                name="total performance limit violation",
                symbol="g_1",
                cons_type=ConstraintTypeEnum.LTE,
                func=total_violation,
                is_linear=False,
                is_convex=False,  # Not checked
                is_twice_differentiable=False,
            )
        ]

    return Problem(
        name="gaa",
        description="The General Aviation Aircraft product family design problem",
        variables=variables,
        objectives=objectives,
        constraints=constraints,
        extra_funcs=extras,
    )
