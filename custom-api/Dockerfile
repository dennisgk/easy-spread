FROM public.ecr.aws/z7e3d4w1/quadratic-api:latest

# Patch hasReachedFileLimit in-place in billing.js
RUN perl -0pi -e 's@if \(!isPrivate\) {\s*return totalTeamFiles >= maxTotalFiles;\s*}\s*return userPrivateFiles >= maxUserPrivateFiles;@if (!isPrivate) {\n        return false;\n    }\n    return false;@s' \
  /quadratic/quadratic-api/dist/src/utils/billing.js

COPY ./customCode.GET.js /quadratic/dist/src/routes/v0/customCode.GET.js
COPY ./custom.py /quadratic/dist/src/routes/v0/custom.py

RUN code=$(base64 -w0 /quadratic/dist/src/routes/v0/custom.py) && \
    sed -i "s|INSERT_CUSTOM_CODE_HERE|$code|" /quadratic/dist/src/routes/v0/customCode.GET.js && \
    rm /quadratic/dist/src/routes/v0/custom.py

FROM public.ecr.aws/z7e3d4w1/quadratic-client:latest

# Add your worker patch script temporarily
COPY worker-patch.js /usr/share/nginx/html/worker-patch.js

# Install brotli (Alpine or Debian)
RUN set -eux; \
  if command -v apk >/dev/null 2>&1; then \
    apk add --no-cache brotli; \
  elif command -v apt-get >/dev/null 2>&1; then \
    apt-get update; \
    apt-get install -y --no-install-recommends brotli; \
    rm -rf /var/lib/apt/lists/*; \
  fi

# Inject <script src="/worker-patch.js"></script> FIRST in <head>
# Then generate index.gz and index.br
# Finally delete worker-patch.js
RUN set -eux; \
  INDEX=/usr/share/nginx/html/index.html; \
  sed -i 's#<head[^>]*>#&\n  <script src="/worker-patch.js"></script>#' "$INDEX"; \
  \
  # Build compressed versions from modified index.html
  gzip -k -f "$INDEX"; \
  mv "$INDEX.gz" /usr/share/nginx/html/index.gz; \
  brotli -f "$INDEX" -o /usr/share/nginx/html/index.br; \
  \
  # Remove the patch file (script tag stays in index)
  rm -f /usr/share/nginx/html/worker-patch.js
