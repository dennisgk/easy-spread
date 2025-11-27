FROM public.ecr.aws/z7e3d4w1/quadratic-api:latest

# Patch hasReachedFileLimit in-place in billing.js
RUN perl -0pi -e 's@if \(!isPrivate\) {\s*return totalTeamFiles >= maxTotalFiles;\s*}\s*return userPrivateFiles >= maxUserPrivateFiles;@if (!isPrivate) {\n        return false;\n    }\n    return false;@s' \
  /quadratic/quadratic-api/dist/src/utils/billing.js
