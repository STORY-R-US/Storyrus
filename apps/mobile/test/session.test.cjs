const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const root = path.resolve(__dirname, "..");
function expiredToken() {
  return `e30.${Buffer.from(JSON.stringify({ sub: "u1", exp: Date.now() / 1000 - 10 })).toString("base64url")}.sig`;
}
function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
function harness(initialToken = "existing-token") {
  let stored = initialToken;
  let fetcher = async () => json({ is_guest: false, email_verified: true });
  const shared = { console, Error, TypeError, FormData, Blob, Headers, Response, AbortController, atob, btoa, setTimeout, clearTimeout };
  function compile(relative, mocks) {
    const filename = path.join(root, relative);
    const exports = {};
    const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    vm.runInNewContext(source, { ...shared, exports, module: { exports }, process: { env: {} },
      fetch: (...args) => fetcher(...args), require: (id) => {
        if (!(id in mocks)) throw new Error(`Unexpected dependency: ${id}`);
        return mocks[id];
      } }, { filename });
    return exports;
  }
  const api = compile("src/api.ts", {
    "@react-native-async-storage/async-storage": { default: {
      getItem: async () => stored, setItem: async (_key, value) => { stored = value; },
      removeItem: async () => { stored = null; },
    } },
    "expo-constants": { default: { expoConfig: {} } },
  });
  return { api, compile, stored: () => stored, fetch: (implementation) => { fetcher = implementation; } };
}

for (const status of [429, 502, 503]) {
  test(`temporary resume HTTP ${status} keeps the stored account`, async () => {
    const old = expiredToken();
    const h = harness(old);
    h.fetch(async () => json({ detail: "Temporarily unavailable" }, status));
    await assert.rejects(h.api.ensureSession(), (error) => error.status === status);
    assert.equal(h.api.getToken(), old);
    assert.equal(h.stored(), old);
  });
}
test("network failure during resume keeps the stored account", async () => {
  const old = expiredToken();
  const h = harness(old);
  h.fetch(async () => { throw new TypeError("Network request failed"); });
  await assert.rejects(h.api.ensureSession(), /Network request failed/);
  assert.equal(h.stored(), old);
});
for (const status of [401, 403]) {
  test(`rejected resume HTTP ${status} clears the stored account`, async () => {
    const h = harness(expiredToken());
    h.fetch(async () => json({ detail: "Invalid session" }, status));
    await assert.rejects(h.api.ensureSession(), (error) => error.status === 401);
    assert.equal(h.api.getToken(), null);
    assert.equal(h.stored(), null);
  });
}
test("malformed renewal does not replace the saved token", async () => {
  const old = expiredToken();
  const h = harness(old);
  h.fetch(async () => json({}));
  await assert.rejects(h.api.ensureSession(), (error) => error.status === 502);
  assert.equal(h.stored(), old);
});
test("a rejected photo upload remains an error", async () => {
  const h = harness();
  h.fetch(async (url) => url.startsWith("file:") ? { blob: async () => new Blob(["photo"]) } : json({}, 403));
  await assert.rejects(h.api.api.uploadToSignedUrl("https://storage.invalid/upload", "file:///photo.jpg", "image/jpeg"),
    (error) => error.status === 403);
});
test("a network failure during photo upload reaches the caller", async () => {
  const h = harness();
  h.fetch(async (url) => {
    if (url.startsWith("file:")) return { blob: async () => new Blob(["photo"]) };
    throw new TypeError("Network request failed");
  });
  await assert.rejects(h.api.api.uploadToSignedUrl("https://storage.invalid/upload", "file:///photo.jpg", "image/jpeg"), /Network request failed/);
});
test("a successful photo upload sends the image bytes", async () => {
  const h = harness();
  const calls = [];
  h.fetch(async (url, init) => {
    calls.push({ url, init });
    return url.startsWith("file:") ? { blob: async () => new Blob(["photo"]) } : new Response(null, { status: 200 });
  });
  await h.api.api.uploadToSignedUrl("https://storage.invalid/upload", "file:///photo.jpg", "image/jpeg");
  assert.equal(calls[1].init.method, "PUT");
  assert.equal(await calls[1].init.body.text(), "photo");
});

function appHarness(h) {
  const values = [];
  const effects = [];
  let index = 0;
  const jsx = (type, props) => ({ type, props });
  const app = h.compile("App.tsx", {
    "./src/api": h.api,
    react: {
      useState: (initial) => {
        const slot = index++;
        if (!(slot in values)) values[slot] = initial;
        return [values[slot], (value) => { values[slot] = typeof value === "function" ? value(values[slot]) : value; }];
      },
      useEffect: (effect) => effects.push(effect),
    },
    "react/jsx-runtime": { jsx, jsxs: jsx },
    "react-native": { StyleSheet: { create: (value) => value }, ActivityIndicator: "ActivityIndicator", Pressable: "Pressable",
      SafeAreaView: "SafeAreaView", Text: "Text", View: "View" },
    "expo-status-bar": { StatusBar: "StatusBar" },
    "./src/AuthScreen": { AuthScreen: "AuthScreen" },
    "./src/StudioScreen": { StudioScreen: "StudioScreen" },
  });
  return {
    render: () => { index = 0; return app.default(); },
    boot: async () => { effects.at(-1)(); await new Promise(setImmediate); },
  };
}
function find(tree, predicate) {
  if (!tree || typeof tree !== "object") return undefined;
  if (predicate(tree)) return tree;
  const children = tree.props?.children;
  for (const child of Array.isArray(children) ? children : [children]) {
    const match = find(child, predicate);
    if (match) return match;
  }
}
test("offline boot preserves the account and retry opens the studio", async () => {
  const h = harness();
  h.fetch(async () => { throw new TypeError("Network request failed"); });
  const app = appHarness(h);
  app.render();
  await app.boot();
  const failed = app.render();
  assert.equal(h.stored(), "existing-token");
  assert.ok(find(failed, (node) => node.props?.accessibilityRole === "alert"));
  assert.equal(find(failed, (node) => node.type === "AuthScreen"), undefined);
  h.fetch(async () => json({ is_guest: false, email_verified: true }));
  find(failed, (node) => node.type === "Pressable").props.onPress();
  app.render();
  await app.boot();
  assert.ok(find(app.render(), (node) => node.type === "StudioScreen"));
  assert.equal(h.stored(), "existing-token");
});
test("boot with a rejected account returns to login", async () => {
  const h = harness();
  h.fetch(async () => json({ detail: "Invalid token" }, 401));
  const app = appHarness(h);
  app.render();
  await app.boot();
  assert.ok(find(app.render(), (node) => node.type === "AuthScreen"));
  assert.equal(h.stored(), null);
});
