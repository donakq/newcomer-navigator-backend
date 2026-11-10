// Which backend this page talks to, chosen by where the page is served from.
// The real frontend should keep the same mapping (e.g. via an env var per Vercel project).
const API_BASE = (() => {
  const host = location.hostname;
  if (host === "localhost" || host === "127.0.0.1") return "http://127.0.0.1:8000";
  if (host.includes("preprod")) return "https://newcomer-navigator-preprod.vercel.app";
  return "https://newcomer-navigator-backend.vercel.app";
})();
