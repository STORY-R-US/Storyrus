import { describe, expect, it } from "vitest";
import { formatPhone, phonePlaceholder, reformatPhone } from "./phoneFormat";

function typed(text: string, country: string): string {
  let value = "";
  for (const ch of text) value = formatPhone(value + ch, country);
  return value;
}

describe("formatPhone", () => {
  it("formata celular e fixo do Brasil com o código do país", () => {
    expect(formatPhone("11988887777", "BR")).toBe("+55 (11) 98888-7777");
    expect(formatPhone("1138887777", "BR")).toBe("+55 (11) 3888-7777");
    expect(formatPhone("+5511988887777", "BR")).toBe("+55 (11) 98888-7777");
  });

  it("formata enquanto a pessoa digita, com ou sem o +55", () => {
    expect(typed("11988887777", "BR")).toBe("+55 (11) 98888-7777");
    expect(typed("+5511988887777", "BR")).toBe("+55 (11) 98888-7777");
    expect(typed("5599887766", "BR")).toBe("+55 (55) 9988-7766");
  });

  it("formata Estados Unidos, Chile e México", () => {
    expect(formatPhone("5551234567", "US")).toBe("+1 (555) 123-4567");
    expect(formatPhone("+15551234567", "US")).toBe("+1 (555) 123-4567");
    expect(typed("15551234567", "US")).toBe("+1 (555) 123-4567");
    expect(formatPhone("912345678", "CL")).toBe("+56 9 1234 5678");
    expect(formatPhone("5512345678", "MX")).toBe("+52 55 1234 5678");
  });

  it("deixa apagar caractere por caractere", () => {
    let value = "+55 (11) 9";
    for (let i = 0; i < 12 && value; i += 1) {
      const next = formatPhone(value.slice(0, -1), "BR");
      expect(next.length).toBeLessThan(value.length);
      value = next;
    }
    expect(value).toBe("");
  });

  it("não inventa formato para país sem regra", () => {
    expect(formatPhone("+81 90 1234 5678", "JP")).toBe("+81 90 1234 5678");
  });
});

describe("reformatPhone", () => {
  it("troca o código e o formato ao mudar o país", () => {
    expect(reformatPhone("+55 (15) 55123-4567", "BR", "US")).toBe("+1 (555) 123-4567");
    expect(reformatPhone("", "BR", "US")).toBe("");
  });
});

describe("phonePlaceholder", () => {
  it("mostra o exemplo com o código do país", () => {
    expect(phonePlaceholder("BR")).toBe("+55 (11) 99999-9999");
    expect(phonePlaceholder("US")).toBe("+1 (555) 123-4567");
  });
});
