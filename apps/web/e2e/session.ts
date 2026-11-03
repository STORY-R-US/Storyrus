// Sessão sintética para a API interceptada pelo Playwright.
// Não tem assinatura válida para um servidor real.
export const TEST_SESSION_TOKEN = [
  Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT" })).toString("base64url"),
  Buffer.from(JSON.stringify({ sub: "user_browser_test", exp: 4102444800 })).toString("base64url"),
  "test-signature",
].join(".");
