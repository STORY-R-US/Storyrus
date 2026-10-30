import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as connection from "./backendConnection";
import { api, setToken } from "./api";
import { legalDocument } from "./legalCopy";
import { PRIVACY_NOTICE_VERSION } from "./privacyNotice";

beforeEach(() => setToken("adult-test-session"));
afterEach(() => vi.restoreAllMocks());

function captureForm(callback: (form: FormData) => void) {
  vi.spyOn(connection, "backendFetch").mockImplementation(async (_input, init) => {
    callback(init!.body as FormData);
    return new Response(JSON.stringify({ id: "media", asset_id: "photo" }), {
      status: 201, headers: { "Content-Type": "application/json" },
    });
  });
}

describe("Explicit media authorization", () => {
  it.each([true, false])("sends the actual photo authorization choice (%s)", async (guardianConsent) => {
    let form: FormData | undefined;
    captureForm((next) => { form = next; });
    await api.uploadPhoto("photo-test", new File(["image"], "photo.jpg", { type: "image/jpeg" }), { guardianConsent });
    expect(form!.get("guardian_consent")).toBe(String(guardianConsent));
    expect(form!.get("consent_version")).toBe(PRIVACY_NOTICE_VERSION);
  });

  it("requires the explicit adult-voice choice independently", async () => {
    let form: FormData | undefined;
    captureForm((next) => { form = next; });
    await api.uploadVoice(new File(["voice"], "adult.mp3", { type: "audio/mpeg" }), "Adult", false, true);
    expect(form!.get("adult_voice_consent")).toBe("true");
    expect(form!.get("consent_version")).toBe(PRIVACY_NOTICE_VERSION);
  });

  it("never fabricates authorization when the caller omits it", async () => {
    let form: FormData | undefined;
    captureForm((next) => { form = next; });
    await api.uploadVoice(new File(["voice"], "adult.mp3"), "Adult");
    expect(form!.get("adult_voice_consent")).toBe("false");
  });
});

describe("Adult-only privacy information", () => {
  it.each(["pt", "en", "es"] as const)("documents the actual safeguards in %s", (lang) => {
    const doc = legalDocument(lang, "privacy");
    const text = JSON.stringify(doc);
    expect(text).toContain("18");
    expect(text).toContain("Kling");
    expect(text).toContain("ElevenLabs");
    expect(text).toContain("OpenAI");
    expect(text).toContain("info@storyrus.ai");
    expect(doc.updated).toContain("29");
  });
});
