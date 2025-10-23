(() => {
  const STORAGE_KEY = "bridge_secret";
  const originalFetch = window.fetch.bind(window);

  function getSecret() {
    return localStorage.getItem(STORAGE_KEY) || "";
  }

  function setSecret(value) {
    if (value && value.trim()) {
      localStorage.setItem(STORAGE_KEY, value.trim());
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  async function executeFetch(input, init, allowRetry) {
    const options = Object.assign({}, init || {});
    options.headers = new Headers((init && init.headers) || {});
    const secret = getSecret();
    if (secret) {
      options.headers.set("X-Bridge-Secret", secret);
    }
    const hasBody = Object.prototype.hasOwnProperty.call(options, "body");
    const method = (options.method || "GET").toUpperCase();
    if (
      hasBody &&
      method !== "GET" &&
      !(options.body instanceof FormData) &&
      !options.headers.has("Content-Type")
    ) {
      options.headers.set("Content-Type", "application/json");
    }

    const response = await originalFetch(input, options);
    if (response.status !== 401 || !allowRetry) {
      return response;
    }

    if (secret) {
      setSecret("");
      alert("Stored bridge API secret was rejected. Please re-enter.");
    }
    const entered = window.prompt("Bridge API secret:");
    if (entered && entered.trim()) {
      setSecret(entered);
      return executeFetch(input, init, false);
    }

    return response;
  }

  window.fetch = function patchedFetch(input, init) {
    return executeFetch(input, init, true);
  };

  window.getBridgeSecret = getSecret;
  window.setBridgeSecret = setSecret;
})();
