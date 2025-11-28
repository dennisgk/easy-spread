// worker-patch.js
(function () {
  // Save the original Worker constructor
  const OriginalWorker = window.Worker;

  function PatchedWorker(scriptURL, options) {
    // Normalize options
    const opts = options ? { ...options } : {};

    // Force credentials to "include" if not already set
    if (opts.credentials === undefined) {
      opts.credentials = "include";
    }

    // OPTIONAL: if you want to default to module workers too:
    // if (opts.type === undefined) {
    //   opts.type = "module";
    // }

    // Create the real worker
    return new OriginalWorker(scriptURL, opts);
  }

  // Preserve prototype so instanceof checks, etc., still work
  PatchedWorker.prototype = OriginalWorker.prototype;

  // Replace global Worker
  window.Worker = PatchedWorker;
})();
