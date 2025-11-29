// worker-patch.js
(function () {
  const OriginalWorker = window.Worker;

  function PatchedWorker(scriptURL, options) {
    const worker = new OriginalWorker(scriptURL, options ?? {});
    const originalPostMessage = worker.postMessage.bind(worker);
    const originalAddEventListener = worker.addEventListener.bind(worker);
    const originalRemoveEventListener = worker.removeEventListener.bind(worker);

    const messageHandlers = new Set(); // all app-side "message" handlers
    let onmessageHandler = null;

    function dispatchToHandlers(event) {
      for (const handler of messageHandlers) {
        try {
          handler.call(worker, event);
        } catch (err) {
          console.error("Error in worker message handler:", err);
        }
      }
    }

    // Single real listener that does the filtering
    originalAddEventListener("message", (event) => {
      const data = event.data;
      const type = data && typeof data === "object" ? data.type : undefined;

      if (type === "ory_tmp_auth_header") {
        const value = sessionStorage.getItem("ory_tmp_auth_header");
        originalPostMessage({
          type: "ory_tmp_auth_header_response",
          value,
          request_id: data && "request_id" in data ? data.request_id : null,
        });
        // Swallow this request completely: no app-side router sees it.
        return;
      }

      // Everything else goes through the app handlers
      dispatchToHandlers(event);
    });

    // Patch addEventListener to intercept *message* only.
    worker.addEventListener = function (type, handler, options) {
      if (type === "message") {
        if (typeof handler === "function") {
          messageHandlers.add(handler);
        }
        // We do NOT call the original addEventListener for "message";
        // the single real listener above will fan-out to all handlers.
        return;
      }
      return originalAddEventListener(type, handler, options);
    };

    // Patch removeEventListener so things that expect to unsubscribe still work.
    worker.removeEventListener = function (type, handler, options) {
      if (type === "message") {
        messageHandlers.delete(handler);
        return;
      }
      return originalRemoveEventListener(type, handler, options);
    };

    // Patch onmessage to go through the same registry.
    Object.defineProperty(worker, "onmessage", {
      configurable: true,
      enumerable: true,
      get() {
        return onmessageHandler;
      },
      set(handler) {
        // Remove previous onmessage from the set if present
        if (onmessageHandler) {
          messageHandlers.delete(onmessageHandler);
        }

        if (typeof handler === "function") {
          onmessageHandler = handler;
          messageHandlers.add(handler);
        } else {
          onmessageHandler = null;
        }
      },
    });

    return worker;
  }

  PatchedWorker.prototype = OriginalWorker.prototype;
  PatchedWorker.prototype.constructor = PatchedWorker;

  // Apply globally
  window.Worker = PatchedWorker;

  const TARGET_HOST = "quadraticapi.kountouris.org";

  const { fetch: originalFetch } = window;

  window.fetch = async (input, init = {}) => {
    const response = await originalFetch(input, init);

    // Only care about requests to the API domain
    const url = typeof input === "string" ? input : input.url || "";
    if (!url.includes(TARGET_HOST)) return response;

    // Normalize headers (init.headers can be object, Headers instance, or array)
    let authHeader = null;
    if (init.headers) {
      if (init.headers instanceof Headers) {
        authHeader = init.headers.get("authorization") || init.headers.get("Authorization");
      } else if (Array.isArray(init.headers)) {
        const authEntry = init.headers.find(([key]) => key.toLowerCase() === "authorization");
        authHeader = authEntry ? authEntry[1] : null;
      } else if (typeof init.headers === "object") {
        authHeader = init.headers.authorization || init.headers.Authorization || null;
      }
    }

    if (authHeader && authHeader.toLowerCase().startsWith("bearer ")) {
      const token = authHeader.slice(7).trim();
      sessionStorage.setItem("ory_tmp_auth_header", token);
    }

    return response;
  };
})();
