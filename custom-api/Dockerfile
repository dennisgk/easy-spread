# -------------------------------
# Stage 1 — Build python-wasm wheel
# -------------------------------
FROM python:3.13-bookworm AS pybuild

WORKDIR /
COPY ./custom_pkgs /custom_pkgs
COPY ./make_custom.py /make_custom.py
COPY ./customCode.GET.js /customCode.GET.js
RUN python3 make_custom.py

########################################
# STEP 1: builder – do ALL the mutations
########################################
FROM public.ecr.aws/z7e3d4w1/quadratic-api:latest AS builder

# Patch hasReachedFileLimit in-place in billing.js
RUN perl -0pi -e 's@if \(!isPrivate\) {\s*return totalTeamFiles >= maxTotalFiles;\s*}\s*return userPrivateFiles >= maxUserPrivateFiles;@if (!isPrivate) {\n        return false;\n    }\n    return false;@s' \
  /quadratic/quadratic-api/dist/src/utils/billing.js

########################################
# STEP 2: final image – copy only changed files
########################################
FROM public.ecr.aws/z7e3d4w1/quadratic-api:latest

# Copy over JUST the stuff the builder changed
COPY --from=builder /quadratic/quadratic-api/dist/src/utils/billing.js \
                    /quadratic/quadratic-api/dist/src/utils/billing.js
COPY --from=pybuild /customCode.GET.js \
                    /quadratic/quadratic-api/dist/src/routes/v0/customCode.GET.js
