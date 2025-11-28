# -------------------------------
# Stage 1 — Build python-wasm wheel
# -------------------------------
FROM ubuntu:24.04 AS builder

# Install tools
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Clone quadratic repo
RUN git clone https://github.com/quadratichq/quadratic.git /quadratic

# Copy your patch files INTO the python-wasm kernel source
COPY ./mpl_patch.py   /quadratic/quadratic-kernels/python-wasm/quadratic_py/mpl_patch.py
COPY ./run_python.py  /quadratic/quadratic-kernels/python-wasm/quadratic_py/run_python.py

# Build the python-wasm kernel
WORKDIR /quadratic/quadratic-kernels/python-wasm
RUN npm install
RUN npm run build

# The built Python wheels appear in ./dist/*.whl
# we leave them for later copying


# ----------------------------------
# Stage 2 — Final Nginx-based client
# ----------------------------------
FROM public.ecr.aws/z7e3d4w1/quadratic-client:latest

# Copy the newly built wheels from the builder
# This overwrites any wheel with same filename
COPY --from=builder /quadratic/quadratic-kernels/python-wasm/dist/*.whl \
    /usr/share/nginx/html/

