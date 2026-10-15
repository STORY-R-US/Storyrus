import type { Lang } from "./i18n/lang";

export type CountryOption = {
  code: string;
  label: Record<Lang, string>;
};

export type CountryGroup = {
  id: "americas" | "europe" | "other";
  label: Record<Lang, string>;
  countries: CountryOption[];
};

export type RegionOption = { value: string; label: string };

export type AddressLayout = "latam" | "us";

export type RegionProfile = {
  layout: AddressLayout;
  postalLabel: Record<Lang, string>;
  postalPlaceholder: string;
  streetPlaceholder: Record<Lang, string>;
  numberLabel: Record<Lang, string>;
  numberPlaceholder: Record<Lang, string>;
  numberRequired: boolean;
  complementLabel: Record<Lang, string>;
  showComplement: boolean;
  districtLabel: Record<Lang, string>;
  showDistrict: boolean;
  districtRequired: boolean;
  stateLabel: Record<Lang, string>;
  stateOptions?: RegionOption[];
  phonePlaceholder: string;
};

const L = (pt: string, en: string, es: string): Record<Lang, string> => ({ pt, en, es });

const US_STATES: RegionOption[] = [
  { value: "AL", label: "Alabama" },
  { value: "AK", label: "Alaska" },
  { value: "AZ", label: "Arizona" },
  { value: "AR", label: "Arkansas" },
  { value: "CA", label: "California" },
  { value: "CO", label: "Colorado" },
  { value: "CT", label: "Connecticut" },
  { value: "DE", label: "Delaware" },
  { value: "DC", label: "District of Columbia" },
  { value: "FL", label: "Florida" },
  { value: "GA", label: "Georgia" },
  { value: "HI", label: "Hawaii" },
  { value: "ID", label: "Idaho" },
  { value: "IL", label: "Illinois" },
  { value: "IN", label: "Indiana" },
  { value: "IA", label: "Iowa" },
  { value: "KS", label: "Kansas" },
  { value: "KY", label: "Kentucky" },
  { value: "LA", label: "Louisiana" },
  { value: "ME", label: "Maine" },
  { value: "MD", label: "Maryland" },
  { value: "MA", label: "Massachusetts" },
  { value: "MI", label: "Michigan" },
  { value: "MN", label: "Minnesota" },
  { value: "MS", label: "Mississippi" },
  { value: "MO", label: "Missouri" },
  { value: "MT", label: "Montana" },
  { value: "NE", label: "Nebraska" },
  { value: "NV", label: "Nevada" },
  { value: "NH", label: "New Hampshire" },
  { value: "NJ", label: "New Jersey" },
  { value: "NM", label: "New Mexico" },
  { value: "NY", label: "New York" },
  { value: "NC", label: "North Carolina" },
  { value: "ND", label: "North Dakota" },
  { value: "OH", label: "Ohio" },
  { value: "OK", label: "Oklahoma" },
  { value: "OR", label: "Oregon" },
  { value: "PA", label: "Pennsylvania" },
  { value: "RI", label: "Rhode Island" },
  { value: "SC", label: "South Carolina" },
  { value: "SD", label: "South Dakota" },
  { value: "TN", label: "Tennessee" },
  { value: "TX", label: "Texas" },
  { value: "UT", label: "Utah" },
  { value: "VT", label: "Vermont" },
  { value: "VA", label: "Virginia" },
  { value: "WA", label: "Washington" },
  { value: "WV", label: "West Virginia" },
  { value: "WI", label: "Wisconsin" },
  { value: "WY", label: "Wyoming" },
];

const BR_UFS: RegionOption[] = [
  { value: "AC", label: "AC" },
  { value: "AL", label: "AL" },
  { value: "AP", label: "AP" },
  { value: "AM", label: "AM" },
  { value: "BA", label: "BA" },
  { value: "CE", label: "CE" },
  { value: "DF", label: "DF" },
  { value: "ES", label: "ES" },
  { value: "GO", label: "GO" },
  { value: "MA", label: "MA" },
  { value: "MT", label: "MT" },
  { value: "MS", label: "MS" },
  { value: "MG", label: "MG" },
  { value: "PA", label: "PA" },
  { value: "PB", label: "PB" },
  { value: "PR", label: "PR" },
  { value: "PE", label: "PE" },
  { value: "PI", label: "PI" },
  { value: "RJ", label: "RJ" },
  { value: "RN", label: "RN" },
  { value: "RS", label: "RS" },
  { value: "RO", label: "RO" },
  { value: "RR", label: "RR" },
  { value: "SC", label: "SC" },
  { value: "SP", label: "SP" },
  { value: "SE", label: "SE" },
  { value: "TO", label: "TO" },
];

const MX_STATES: RegionOption[] = [
  { value: "AGU", label: "Aguascalientes" },
  { value: "BCN", label: "Baja California" },
  { value: "BCS", label: "Baja California Sur" },
  { value: "CAM", label: "Campeche" },
  { value: "CHP", label: "Chiapas" },
  { value: "CHH", label: "Chihuahua" },
  { value: "CMX", label: "Ciudad de México" },
  { value: "COA", label: "Coahuila" },
  { value: "COL", label: "Colima" },
  { value: "DUR", label: "Durango" },
  { value: "GTO", label: "Guanajuato" },
  { value: "GRO", label: "Guerrero" },
  { value: "HID", label: "Hidalgo" },
  { value: "JAL", label: "Jalisco" },
  { value: "MEX", label: "Estado de México" },
  { value: "MIC", label: "Michoacán" },
  { value: "MOR", label: "Morelos" },
  { value: "NAY", label: "Nayarit" },
  { value: "NLE", label: "Nuevo León" },
  { value: "OAX", label: "Oaxaca" },
  { value: "PUE", label: "Puebla" },
  { value: "QUE", label: "Querétaro" },
  { value: "ROO", label: "Quintana Roo" },
  { value: "SLP", label: "San Luis Potosí" },
  { value: "SIN", label: "Sinaloa" },
  { value: "SON", label: "Sonora" },
  { value: "TAB", label: "Tabasco" },
  { value: "TAM", label: "Tamaulipas" },
  { value: "TLA", label: "Tlaxcala" },
  { value: "VER", label: "Veracruz" },
  { value: "YUC", label: "Yucatán" },
  { value: "ZAC", label: "Zacatecas" },
];

const AR_PROVINCES: RegionOption[] = [
  { value: "CABA", label: "CABA" },
  { value: "Buenos Aires", label: "Buenos Aires" },
  { value: "Catamarca", label: "Catamarca" },
  { value: "Chaco", label: "Chaco" },
  { value: "Chubut", label: "Chubut" },
  { value: "Córdoba", label: "Córdoba" },
  { value: "Corrientes", label: "Corrientes" },
  { value: "Entre Ríos", label: "Entre Ríos" },
  { value: "Formosa", label: "Formosa" },
  { value: "Jujuy", label: "Jujuy" },
  { value: "La Pampa", label: "La Pampa" },
  { value: "La Rioja", label: "La Rioja" },
  { value: "Mendoza", label: "Mendoza" },
  { value: "Misiones", label: "Misiones" },
  { value: "Neuquén", label: "Neuquén" },
  { value: "Río Negro", label: "Río Negro" },
  { value: "Salta", label: "Salta" },
  { value: "San Juan", label: "San Juan" },
  { value: "San Luis", label: "San Luis" },
  { value: "Santa Cruz", label: "Santa Cruz" },
  { value: "Santa Fe", label: "Santa Fe" },
  { value: "Santiago del Estero", label: "Santiago del Estero" },
  { value: "Tierra del Fuego", label: "Tierra del Fuego" },
  { value: "Tucumán", label: "Tucumán" },
];

function latam(overrides: Partial<RegionProfile> = {}): RegionProfile {
  return {
    layout: "latam",
    postalLabel: L("Código Postal", "Postal Code", "Código Postal"),
    postalPlaceholder: "00000",
    streetPlaceholder: L("Rua, avenida…", "Street name", "Calle, avenida…"),
    numberLabel: L("Número", "Number", "Número"),
    numberPlaceholder: L("123", "123", "123"),
    numberRequired: true,
    complementLabel: L("Complemento (Opcional)", "Apt / Unit (Optional)", "Complemento (Opcional)"),
    showComplement: true,
    districtLabel: L("Bairro (Opcional)", "Neighborhood (Optional)", "Barrio (Opcional)"),
    showDistrict: true,
    districtRequired: false,
    stateLabel: L("Estado / Região", "State / Region", "Estado / Región"),
    phonePlaceholder: "+00 000 000 0000",
    ...overrides,
  };
}

const PROFILES: Record<string, RegionProfile> = {
  BR: latam({
    postalLabel: L("CEP", "ZIP (CEP)", "CEP"),
    postalPlaceholder: "01310-100",
    streetPlaceholder: L("Av. Paulista", "Av. Paulista", "Av. Paulista"),
    districtLabel: L("Bairro", "Neighborhood", "Barrio"),
    districtRequired: true,
    stateLabel: L("UF", "State (UF)", "UF"),
    stateOptions: BR_UFS,
    phonePlaceholder: "(11) 99999-9999",
  }),
  US: {
    layout: "us",
    postalLabel: L("ZIP", "ZIP Code", "ZIP"),
    postalPlaceholder: "90210",
    streetPlaceholder: L("100 Rodeo Drive", "100 Rodeo Drive", "100 Rodeo Drive"),
    numberLabel: L("Apto / Unidade (Opcional)", "Apt / Suite (Optional)", "Apto / Unidad (Opcional)"),
    numberPlaceholder: L("Apto 4B", "Apt 4B", "Apto 4B"),
    numberRequired: false,
    complementLabel: L("Complemento", "Apt / suite", "Complemento"),
    showComplement: false,
    districtLabel: L("Bairro", "Neighborhood", "Barrio"),
    showDistrict: false,
    districtRequired: false,
    stateLabel: L("Estado", "State", "Estado"),
    stateOptions: US_STATES,
    phonePlaceholder: "(555) 123-4567",
  },
  MX: latam({
    postalLabel: L("Código Postal", "Postal Code", "Código Postal"),
    postalPlaceholder: "06600",
    streetPlaceholder: L("Av. Reforma", "Av. Reforma", "Av. Reforma"),
    districtLabel: L("Colonia (Opcional)", "Colonia (Optional)", "Colonia (Opcional)"),
    stateLabel: L("Estado", "State", "Estado"),
    stateOptions: MX_STATES,
    phonePlaceholder: "55 1234 5678",
  }),
  AR: latam({
    postalLabel: L("CPA / Código Postal", "Postal Code", "CPA / Código Postal"),
    postalPlaceholder: "C1000",
    streetPlaceholder: L("Av. Corrientes", "Av. Corrientes", "Av. Corrientes"),
    districtLabel: L("Barrio (Opcional)", "Barrio (Optional)", "Barrio (Opcional)"),
    stateLabel: L("Província", "Province", "Provincia"),
    stateOptions: AR_PROVINCES,
    phonePlaceholder: "11 1234-5678",
  }),
  CL: latam({
    postalPlaceholder: "8320000",
    districtLabel: L("Comuna (Opcional)", "Comuna (Optional)", "Comuna (Opcional)"),
    stateLabel: L("Região", "Region", "Región"),
    phonePlaceholder: "9 1234 5678",
  }),
  CO: latam({
    postalPlaceholder: "110111",
    districtLabel: L("Barrio (Opcional)", "Barrio (Optional)", "Barrio (Opcional)"),
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "300 123 4567",
  }),
  PE: latam({
    postalPlaceholder: "15001",
    districtLabel: L("Distrito (Opcional)", "District (Optional)", "Distrito (Opcional)"),
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "999 123 456",
  }),
  UY: latam({
    postalPlaceholder: "11000",
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "94 123 456",
  }),
  PY: latam({
    postalPlaceholder: "1209",
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "981 123 456",
  }),
  BO: latam({
    postalPlaceholder: "0000",
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "7 123 4567",
  }),
  EC: latam({
    postalPlaceholder: "170150",
    stateLabel: L("Província", "Province", "Provincia"),
    phonePlaceholder: "99 123 4567",
  }),
  VE: latam({
    postalPlaceholder: "1010",
    stateLabel: L("Estado", "State", "Estado"),
    phonePlaceholder: "412 123 4567",
  }),
  CR: latam({
    postalPlaceholder: "10101",
    districtLabel: L("Distrito (Opcional)", "District (Optional)", "Distrito (Opcional)"),
    stateLabel: L("Província", "Province", "Provincia"),
    phonePlaceholder: "8888 1234",
  }),
  PA: latam({
    postalPlaceholder: "0801",
    stateLabel: L("Província", "Province", "Provincia"),
    phonePlaceholder: "6000 1234",
  }),
  DO: latam({
    postalPlaceholder: "10101",
    stateLabel: L("Província", "Province", "Provincia"),
    phonePlaceholder: "809 123 4567",
  }),
  GT: latam({
    postalPlaceholder: "01001",
    stateLabel: L("Departamento", "Department", "Departamento"),
    phonePlaceholder: "5123 4567",
  }),
  CA: {
    layout: "us",
    postalLabel: L("Código Postal", "Postal Code", "Código Postal"),
    postalPlaceholder: "M5V 3L9",
    streetPlaceholder: L("100 Queen St W", "100 Queen St W", "100 Queen St W"),
    numberLabel: L("Apto / Unidade (Opcional)", "Apt / Suite (Optional)", "Apto / Unidad (Opcional)"),
    numberPlaceholder: L("Apto 4B", "Apt 4B", "Apto 4B"),
    numberRequired: false,
    complementLabel: L("Complemento", "Apt / suite", "Complemento"),
    showComplement: false,
    districtLabel: L("Bairro", "Neighborhood", "Barrio"),
    showDistrict: false,
    districtRequired: false,
    stateLabel: L("Província", "Province", "Provincia"),
    phonePlaceholder: "(416) 555-0123",
  },
};

export const COUNTRY_GROUPS: CountryGroup[] = [
  {
    id: "americas",
    label: L("Américas", "Americas", "Américas"),
    countries: [
      { code: "BR", label: L("Brasil", "Brazil", "Brasil") },
      { code: "US", label: L("Estados Unidos", "United States", "Estados Unidos") },
      { code: "MX", label: L("México", "Mexico", "México") },
      { code: "AR", label: L("Argentina", "Argentina", "Argentina") },
      { code: "CL", label: L("Chile", "Chile", "Chile") },
      { code: "CO", label: L("Colômbia", "Colombia", "Colombia") },
      { code: "PE", label: L("Peru", "Peru", "Perú") },
      { code: "UY", label: L("Uruguai", "Uruguay", "Uruguay") },
      { code: "PY", label: L("Paraguai", "Paraguay", "Paraguay") },
      { code: "BO", label: L("Bolívia", "Bolivia", "Bolivia") },
      { code: "EC", label: L("Equador", "Ecuador", "Ecuador") },
      { code: "VE", label: L("Venezuela", "Venezuela", "Venezuela") },
      { code: "CR", label: L("Costa Rica", "Costa Rica", "Costa Rica") },
      { code: "PA", label: L("Panamá", "Panama", "Panamá") },
      { code: "DO", label: L("República Dominicana", "Dominican Republic", "República Dominicana") },
      { code: "GT", label: L("Guatemala", "Guatemala", "Guatemala") },
      { code: "CA", label: L("Canadá", "Canada", "Canadá") },
    ],
  },
  {
    id: "europe",
    label: L("Europa", "Europe", "Europa"),
    countries: [
      { code: "PT", label: L("Portugal", "Portugal", "Portugal") },
      { code: "ES", label: L("Espanha", "Spain", "España") },
      { code: "GB", label: L("Reino Unido", "United Kingdom", "Reino Unido") },
      { code: "DE", label: L("Alemanha", "Germany", "Alemania") },
      { code: "FR", label: L("França", "France", "Francia") },
      { code: "IT", label: L("Itália", "Italy", "Italia") },
      { code: "IE", label: L("Irlanda", "Ireland", "Irlanda") },
      { code: "CH", label: L("Suíça", "Switzerland", "Suiza") },
      { code: "NL", label: L("Países Baixos", "Netherlands", "Países Bajos") },
      { code: "BE", label: L("Bélgica", "Belgium", "Bélgica") },
      { code: "SE", label: L("Suécia", "Sweden", "Suecia") },
      { code: "NO", label: L("Noruega", "Norway", "Noruega") },
      { code: "DK", label: L("Dinamarca", "Denmark", "Dinamarca") },
      { code: "FI", label: L("Finlândia", "Finland", "Finlandia") },
      { code: "PL", label: L("Polônia", "Poland", "Polonia") },
    ],
  },
  {
    id: "other",
    label: L("Outros", "Other", "Otros"),
    countries: [
      { code: "AO", label: L("Angola", "Angola", "Angola") },
      { code: "MZ", label: L("Moçambique", "Mozambique", "Mozambique") },
      { code: "ZA", label: L("África do Sul", "South Africa", "Sudáfrica") },
      { code: "AU", label: L("Austrália", "Australia", "Australia") },
      { code: "NZ", label: L("Nova Zelândia", "New Zealand", "Nueva Zelanda") },
      { code: "JP", label: L("Japão", "Japan", "Japón") },
      { code: "KR", label: L("Coreia do Sul", "South Korea", "Corea del Sur") },
      { code: "CN", label: L("China", "China", "China") },
      { code: "IN", label: L("Índia", "India", "India") },
      { code: "SG", label: L("Singapura", "Singapore", "Singapur") },
      { code: "AE", label: L("Emirados Árabes", "United Arab Emirates", "Emiratos Árabes") },
      { code: "IL", label: L("Israel", "Israel", "Israel") },
    ],
  },
];

const FALLBACK = latam();

export function regionProfile(country: string): RegionProfile {
  return PROFILES[country.toUpperCase()] ?? FALLBACK;
}

export function defaultCountry(lang: Lang): string {
  if (lang === "en") return "US";
  if (lang === "es") return "MX";
  return "BR";
}

/** US/CA: número de apto é opcional — o backend exige `number`, então enviamos n/a. */
export function submitStreetNumber(country: string, number: string): string {
  const trimmed = number.trim();
  if (trimmed) return trimmed;
  return regionProfile(country).numberRequired ? "" : "n/a";
}
