import { describe, expect, it } from "vitest";
import { defaultCountry, regionProfile, submitStreetNumber } from "./signupRegions";

describe("signupRegions", () => {
  it("escolhe país padrão por idioma (LATAM + EUA)", () => {
    expect(defaultCountry("pt")).toBe("BR");
    expect(defaultCountry("en")).toBe("US");
    expect(defaultCountry("es")).toBe("MX");
  });

  it("layout EUA esconde bairro e deixa apto opcional", () => {
    const us = regionProfile("US");
    expect(us.layout).toBe("us");
    expect(us.showDistrict).toBe(false);
    expect(us.numberRequired).toBe(false);
    expect(submitStreetNumber("US", "")).toBe("n/a");
    expect(submitStreetNumber("US", "4B")).toBe("4B");
  });

  it("Brasil exige bairro e UF", () => {
    const br = regionProfile("BR");
    expect(br.districtRequired).toBe(true);
    expect(br.stateOptions?.some((o) => o.value === "SP")).toBe(true);
  });
});
