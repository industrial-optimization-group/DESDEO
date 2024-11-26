# This dockerfile the base s2i python 3.12 build image 
# and adds ca-certificates for managing gurobi linces 
# and COIN-OR solvers (most notably bonmin and ipopt)

FROM registry.access.redhat.com/ubi8/python-312

# Ensure we are running as root
USER root

# Update the system and install ca-certificates and wget
RUN dnf update -y && \
    dnf install -y ca-certificates wget && \
    update-ca-trust && \
    dnf clean all

# Define the directory to store binaries and add it to PATH
ENV SOLVER_BINARIES_DIR="/opt/solver_binaries"
ENV PATH="${SOLVER_BINARIES_DIR}/ampl.linux-intel64:$PATH"

# Download and extract the solver binaries to the directory
RUN mkdir -p $SOLVER_BINARIES_DIR && \
    wget -qO- https://github.com/industrial-optimization-group/DESDEO/releases/download/supplementary/solver_binaries.tgz | tar -xz -C $SOLVER_BINARIES_DIR

# Switch back to a non-root user
USER 1001