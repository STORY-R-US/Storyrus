import { expect, test as base } from "@playwright/test";

// Page routes supply synthetic API responses. This lower-priority context route
// blocks any missed API mock before Vite can proxy it to a real backend.
export const test = base.extend({
  context: async ({ context }, use) => {
    const unmockedApi: string[] = [];
    await context.route("**/*", (route) => {
      const url = new URL(route.request().url());
      if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
        return route.abort("blockedbyclient");
      }
      if (url.pathname === "/health") {
        return route.fulfill({ json: { status: "ok" } });
      }
      if (url.pathname === "/v1" || url.pathname.startsWith("/v1/")) {
        unmockedApi.push(`${route.request().method()} ${url.pathname}`);
        return route.abort("blockedbyclient");
      }
      return route.continue();
    });
    await use(context);
    expect(unmockedApi, "Every API call must have a mock; live generation is forbidden").toEqual([]);
  },
});

export { expect };
