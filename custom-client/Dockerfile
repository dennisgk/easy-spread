# -------------------------------
# Stage 1 — Build python-wasm wheel
# -------------------------------
FROM python:3.13-bookworm AS pybuild

RUN set -eux; \
  apt-get update; \
  apt-get install -y curl git nodejs npm; \
  rm -rf /var/lib/apt/lists/*

# Install Poetry (if you haven’t already)
RUN curl -sSL https://install.python-poetry.org | python3 -

# Clone quadratic repo
RUN git clone https://github.com/quadratichq/quadratic.git /quadratic

# Copy your patch files INTO the python-wasm kernel source
COPY ./custom_patch.py   /quadratic/quadratic-kernels/python-wasm/quadratic_py/custom_patch.py
COPY ./mpl_patch.py   /quadratic/quadratic-kernels/python-wasm/quadratic_py/mpl_patch.py
COPY ./run_python.py  /quadratic/quadratic-kernels/python-wasm/quadratic_py/run_python.py

# Tell poetry to use Python 3.13 for that project, then build
RUN set -eux; \
  cd /quadratic/quadratic-kernels/python-wasm/quadratic_py; \
  export PATH="/root/.local/bin:$PATH"; \
  poetry env use python3.13; \
  cd /quadratic/quadratic-kernels/python-wasm; \
  npm install; \
  npm run build

# The built Python wheels appear in ./dist/*.whl
# we leave them for later copying

########################################
# STEP 1: builder – do ALL the mutations
########################################
FROM public.ecr.aws/z7e3d4w1/quadratic-client:latest AS builder

# ---- index*3 builder part (index.html + .gz + .br) ----

# Add your worker patch script temporarily
COPY worker-patch.js /usr/share/nginx/html/worker-patch.js

# Install brotli (Alpine or Debian) in the *builder* only
RUN set -eux; \
  if command -v apk >/dev/null 2>&1; then \
    apk add --no-cache brotli; \
  elif command -v apt-get >/dev/null 2>&1; then \
    apt-get update; \
    apt-get install -y --no-install-recommends brotli; \
    rm -rf /var/lib/apt/lists/*; \
  fi

# Inject <script src="/worker-patch.js"></script> FIRST in <head>
# Then generate index.gz and index.br, then delete worker-patch.js
RUN set -eux; \
  INDEX=/usr/share/nginx/html/index.html; \
  PATCH_PATH=/usr/share/nginx/html/worker-patch.js; \
  TMP=/tmp/inline-patch.html; \
  awk 'BEGIN { print "<script>" } { print } END { print "</script>" }' "$PATCH_PATH" > "$TMP"; \
  sed -i "/<head[^>]*>/r $TMP" "$INDEX"; \
  gzip -k -f "$INDEX"; \
  mv "$INDEX.gz" /usr/share/nginx/html/index.html.gz; \
  brotli -f "$INDEX" -o /usr/share/nginx/html/index.html.br; \
  rm -f "$PATCH_PATH" "$TMP"

# ----------------------------------
# Stage 2 — Final Nginx-based client
# ----------------------------------
FROM public.ecr.aws/z7e3d4w1/quadratic-client:latest

# Copy the newly built wheels from the builder
# This overwrites any wheel with same filename
COPY --from=pybuild /quadratic/quadratic-kernels/python-wasm/dist/*.whl \
    /usr/share/nginx/html/
COPY --from=builder /usr/share/nginx/html/index.html \
                    /usr/share/nginx/html/index.html
COPY --from=builder /usr/share/nginx/html/index.html.gz \
                    /usr/share/nginx/html/index.html.gz
COPY --from=builder /usr/share/nginx/html/index.html.br \
                    /usr/share/nginx/html/index.html.br
