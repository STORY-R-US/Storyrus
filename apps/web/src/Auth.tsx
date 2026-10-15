import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import logo from "./assets/logo.png";
import { api, getToken, type SignupPayload } from "./api";
import { formatPostal, supportsPostalLookup, useCepLookup, type CepStatus } from "./cepLookup";
import {
  LANGS,
  type Lang,
  useResolvedLang,
} from "./i18n/lang";
import {
  COUNTRY_GROUPS,
  defaultCountry,
  regionProfile,
  submitStreetNumber,
} from "./signupRegions";
import { PasswordField } from "./PasswordField";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

export type AuthMode = "login" | "signup";

const COPY: Record<
  Lang,
  {
    loginTitle: string;
    signupTitle: string;
    loginLead: string;
    signupLead: string;
    accountSection: string;
    addressSection: string;
    email: string;
    password: string;
    passwordConfirm: string;
    fullName: string;
    phone: string;
    country: string;
    street: string;
    city: string;
    acceptTerms: string;
    termsAnd: string;
    terms: string;
    privacy: string;
    loginSubmit: string;
    signupSubmit: string;
    busy: string;
    switchToSignup: string;
    switchToLogin: string;
    forgotPassword: string;
    back: string;
    checkTitle: string;
    checkLead: string;
    checkHint: string;
    passwordMismatch: string;
    mustAcceptTerms: string;
    resend: string;
    resendBusy: string;
    resendOk: string;
    langAria: string;
    unavailableSignup: string;
    unavailableLogin: string;
    emailTaken: string;
    confirmEmail: string;
    badCredentials: string;
    genericError: string;
    cepLooking: string;
    cepMiss: string;
    cepError: string;
    cepOk: string;
  }
> = {
  pt: {
    loginTitle: "Entrar",
    signupTitle: "Criar Conta",
    loginLead: "Acesse sua conta para criar livros personalizados.",
    signupLead: "Cadastro pensado para Brasil, América Latina e EUA — usamos estes dados no envio.",
    accountSection: "Sua Conta",
    addressSection: "Endereço De Entrega",
    email: "E-mail",
    password: "Senha (Mín. 8)",
    passwordConfirm: "Confirmar Senha",
    fullName: "Nome Completo",
    phone: "Telefone / WhatsApp",
    country: "País",
    street: "Rua / Avenida",
    city: "Cidade",
    acceptTerms: "Li e aceito os",
    termsAnd: "e a",
    terms: "Termos De Uso",
    privacy: "Política De Privacidade",
    loginSubmit: "Entrar",
    signupSubmit: "Criar Conta",
    busy: "Aguarde…",
    switchToSignup: "Criar Uma Conta",
    switchToLogin: "Já Tenho Conta",
    forgotPassword: "Esqueci A Senha",
    back: "Voltar Ao Início",
    checkTitle: "Verifique Seu E-mail",
    checkLead: "Enviamos um link de confirmação. Ative a conta antes de entrar no estúdio.",
    checkHint: "Não recebeu? Confira o spam ou tente criar a conta de novo em alguns minutos.",
    passwordMismatch: "As senhas não coincidem.",
    mustAcceptTerms: "Aceite os termos e a política de privacidade.",
    resend: "Reenviar E-mail De Confirmação",
    resendBusy: "Enviando…",
    resendOk: "Se a conta estiver pendente, enviamos um novo link.",
    langAria: "Idioma",
    unavailableSignup: "Não foi possível criar a conta agora. O servidor está indisponível — tente de novo em instantes.",
    unavailableLogin: "Não foi possível entrar agora. O servidor está indisponível — tente de novo em instantes.",
    emailTaken: "Este e-mail já tem conta. Tente entrar.",
    confirmEmail: "Confirme seu e-mail pelo link que enviamos antes de entrar.",
    badCredentials: "E-mail ou senha incorretos.",
    genericError: "Algo deu errado. Tente novamente.",
    cepLooking: "Buscando endereço…",
    cepMiss: "CEP não encontrado. Preencha o endereço.",
    cepError: "Não foi possível buscar o CEP. Preencha o endereço.",
    cepOk: "Endereço preenchido. Confira e informe o número.",
  },
  en: {
    loginTitle: "Log In",
    signupTitle: "Create Account",
    loginLead: "Sign in to create personalized books.",
    signupLead: "Built for the US and Latin America — we reuse this for orders and shipping.",
    accountSection: "Your Account",
    addressSection: "Shipping Address",
    email: "Email",
    password: "Password (Min. 8)",
    passwordConfirm: "Confirm Password",
    fullName: "Full Name",
    phone: "Phone / WhatsApp",
    country: "Country",
    street: "Street Address",
    city: "City",
    acceptTerms: "I agree to the",
    termsAnd: "and the",
    terms: "Terms Of Use",
    privacy: "Privacy Policy",
    loginSubmit: "Log In",
    signupSubmit: "Create Account",
    busy: "Please wait…",
    switchToSignup: "Create An Account",
    switchToLogin: "I Already Have An Account",
    forgotPassword: "Forgot Password",
    back: "Back To Home",
    checkTitle: "Check Your Email",
    checkLead: "We sent a confirmation link. Activate your account before opening the studio.",
    checkHint: "Didn't get it? Check spam or try signing up again in a few minutes.",
    passwordMismatch: "Passwords do not match.",
    mustAcceptTerms: "Please accept the terms and privacy policy.",
    resend: "Resend Confirmation Email",
    resendBusy: "Sending…",
    resendOk: "If the account is still pending, we sent a new link.",
    langAria: "Language",
    unavailableSignup: "We couldn’t create the account right now. The server is unavailable — try again in a moment.",
    unavailableLogin: "We couldn’t sign you in right now. The server is unavailable — try again in a moment.",
    emailTaken: "This email already has an account. Try logging in.",
    confirmEmail: "Confirm your email with the link we sent before signing in.",
    badCredentials: "Incorrect email or password.",
    genericError: "Something went wrong. Please try again.",
    cepLooking: "Looking up address…",
    cepMiss: "ZIP/CEP not found. Please fill in the address.",
    cepError: "Could not look up the CEP. Please fill in the address.",
    cepOk: "Address filled in. Check it and add the number.",
  },
  es: {
    loginTitle: "Entrar",
    signupTitle: "Crear Cuenta",
    loginLead: "Accede a tu cuenta para crear libros personalizados.",
    signupLead: "Pensado para Latinoamérica, Brasil y EE. UU. — usamos estos datos en el envío.",
    accountSection: "Tu Cuenta",
    addressSection: "Dirección De Envío",
    email: "Correo",
    password: "Contraseña (Mín. 8)",
    passwordConfirm: "Confirmar Contraseña",
    fullName: "Nombre Completo",
    phone: "Teléfono / WhatsApp",
    country: "País",
    street: "Calle / Avenida",
    city: "Ciudad",
    acceptTerms: "Acepto los",
    termsAnd: "y la",
    terms: "Términos De Uso",
    privacy: "Política De Privacidad",
    loginSubmit: "Entrar",
    signupSubmit: "Crear Cuenta",
    busy: "Espera…",
    switchToSignup: "Crear Una Cuenta",
    switchToLogin: "Ya Tengo Cuenta",
    forgotPassword: "Olvidé La Contraseña",
    back: "Volver Al Inicio",
    checkTitle: "Revisa Tu Correo",
    checkLead: "Enviamos un enlace de confirmación. Activa la cuenta antes de entrar al estudio.",
    checkHint: "¿No llegó? Revisa spam o vuelve a registrarte en unos minutos.",
    passwordMismatch: "Las contraseñas no coinciden.",
    mustAcceptTerms: "Acepta los términos y la política de privacidad.",
    resend: "Reenviar Correo De Confirmación",
    resendBusy: "Enviando…",
    resendOk: "Si la cuenta está pendiente, enviamos un enlace nuevo.",
    langAria: "Idioma",
    unavailableSignup: "No fue posible crear la cuenta ahora. El servidor no está disponible — inténtalo en un momento.",
    unavailableLogin: "No fue posible entrar ahora. El servidor no está disponible — inténtalo en un momento.",
    emailTaken: "Este correo ya tiene cuenta. Intenta entrar.",
    confirmEmail: "Confirma tu correo con el enlace que enviamos antes de entrar.",
    badCredentials: "Correo o contraseña incorrectos.",
    genericError: "Algo salió mal. Inténtalo de nuevo.",
    cepLooking: "Buscando dirección…",
    cepMiss: "CEP no encontrado. Completa la dirección.",
    cepError: "No fue posible buscar el CEP. Completa la dirección.",
    cepOk: "Dirección rellenada. Revisa e indica el número.",
  },
};

function cepStatusText(status: CepStatus, t: (typeof COPY)[Lang]): string | null {
  if (status === "loading") return t.cepLooking;
  if (status === "ok") return t.cepOk;
  if (status === "miss") return t.cepMiss;
  if (status === "error") return t.cepError;
  return null;
}

/** Evita open-redirect: só caminhos relativos internos. Sem next, volta à home. */
export function safeNextPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}

/**
 * Token de e-mail (confirmação / senha). Clientes quebram JWT longo;
 * pega o valor até o próximo parâmetro conhecido e tira espaços.
 */
export function readAuthQueryToken(search: string): string {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const match = raw.match(/(?:^|&)token=([^&]*)/i);
  const value = match?.[1] ?? "";
  let token = value.replace(/\+/g, "%2B");
  try {
    token = decodeURIComponent(token);
  } catch {
    token = value;
  }
  return token.replace(/\s+/g, "").replace(/^<|>$/g, "");
}

export function readAuthQueryEmail(search: string): string {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const params = new URLSearchParams(raw);
  return (params.get("email") || "").trim();
}

/** Encaminha para o cadastro preservando o destino do estúdio. */
export function accountGateHref(nextPath: string): string {
  const next = safeNextPath(nextPath);
  return `/cadastro?next=${encodeURIComponent(next)}`;
}

/** Com sessão local, abre o estúdio; sem token, pede cadastro. */
export function studioEntryHref(nextPath: string): string {
  const next = safeNextPath(nextPath);
  if (getToken()) return next;
  return accountGateHref(next);
}

function emptySignup(lang: Lang) {
  return {
    full_name: "",
    phone: "",
    country: defaultCountry(lang),
    postal_code: "",
    street: "",
    number: "",
    complement: "",
    district: "",
    city: "",
    state: "",
    password_confirm: "",
    accept_terms: false,
  };
}

function LangSwitch({
  lang,
  onChange,
  ariaLabel,
}: {
  lang: Lang;
  onChange: (lang: Lang) => void;
  ariaLabel: string;
}) {
  return (
    <div className="lang auth-lang" role="group" aria-label={ariaLabel} data-testid="auth-lang">
      {LANGS.map((code) => (
        <button
          key={code}
          type="button"
          className={lang === code ? "on" : ""}
          aria-pressed={lang === code}
          onClick={() => onChange(code)}
          data-testid={`auth-lang-${code}`}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export function Auth({ mode }: { mode: AuthMode }) {
  usePageMeta(staticPageMeta(mode === "login" ? "/entrar" : "/cadastro"));
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = useMemo(() => safeNextPath(params.get("next")), [params]);
  const [lang, setLangBase] = useResolvedLang();
  const t = COPY[lang];
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signup, setSignup] = useState(() => emptySignup(lang));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [checkEmail, setCheckEmail] = useState(false);
  const [resendHint, setResendHint] = useState<string | null>(null);

  const region = regionProfile(signup.country);
  const isUsLayout = region.layout === "us";
  const postalLookupOn =
    mode === "signup" && supportsPostalLookup(signup.country);
  const cepStatus = useCepLookup(
    signup.postal_code,
    postalLookupOn,
    (addr) => {
      setSignup((prev) => ({
        ...prev,
        postal_code: addr.postal_code,
        street: addr.street || prev.street,
        district: addr.district || prev.district,
        city: addr.city || prev.city,
        state: addr.state || prev.state,
      }));
    },
    signup.country,
  );

  function onPostalCodeChange(value: string) {
    setSignup((prev) => ({
      ...prev,
      postal_code: formatPostal(value, prev.country),
    }));
  }

  const altMode: AuthMode = mode === "login" ? "signup" : "login";
  const altPath = altMode === "login" ? "/entrar" : "/cadastro";
  const altHref = `${altPath}?next=${encodeURIComponent(next)}`;

  useEffect(() => {
    setSignup((prev) => {
      const stillDefault = !prev.street && !prev.city && !prev.postal_code && !prev.state;
      if (!stillDefault) return prev;
      const nextCountry = defaultCountry(lang);
      if (prev.country === nextCountry) return prev;
      return { ...prev, country: nextCountry, state: "" };
    });
  }, [lang]);

  function setLang(nextLang: Lang) {
    setLangBase(nextLang);
  }

  function onCountryChange(country: string) {
    setSignup((prev) => ({ ...prev, country, state: "", number: prev.number }));
  }

  function friendlyAuthError(raw: string): string {
    const msg = raw.trim();
    if (
      /^502\b|^503\b|^504\b/i.test(msg) ||
      /failed to fetch|networkerror|load failed|demorou demais|abort/i.test(msg)
    ) {
      return mode === "signup" ? t.unavailableSignup : t.unavailableLogin;
    }
    if (/^409\b/i.test(msg)) return t.emailTaken;
    if (/^403\b/i.test(msg) || /confirme seu e-mail|verify|verif/i.test(msg)) {
      return t.confirmEmail;
    }
    if (/^401\b/i.test(msg) || /credencial|senha|password|unauthorized/i.test(msg)) {
      return t.badCredentials;
    }
    const cleaned = msg.replace(/^\d{3}:\s*/i, "").trim();
    return cleaned || msg || t.genericError;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") {
        if (password !== signup.password_confirm) {
          setError(t.passwordMismatch);
          return;
        }
        if (!signup.accept_terms) {
          setError(t.mustAcceptTerms);
          return;
        }
        const payload: SignupPayload = {
          email: email.trim(),
          password,
          password_confirm: signup.password_confirm,
          full_name: signup.full_name.trim(),
          phone: signup.phone.trim(),
          postal_code: signup.postal_code.trim(),
          street: signup.street.trim(),
          number: submitStreetNumber(signup.country, signup.number),
          complement: signup.complement.trim() || null,
          district: signup.district.trim() || null,
          city: signup.city.trim(),
          state: signup.state.trim(),
          country: signup.country.trim().toUpperCase(),
          accept_terms: true,
        };
        await api.signup(payload);
        setCheckEmail(true);
        return;
      }
      await api.login(email.trim(), password);
      navigate(next, { replace: true });
    } catch (err) {
      const raw = (err as Error).message || "";
      if (mode === "login" && (/^403\b/i.test(raw) || /confirme seu e-mail|verify|verif/i.test(raw))) {
        setCheckEmail(true);
        return;
      }
      setError(friendlyAuthError(raw));
    } finally {
      setBusy(false);
    }
  }

  async function onResend() {
    const dest = email.trim();
    if (!dest) return;
    setBusy(true);
    setResendHint(null);
    try {
      await api.resendVerify(dest);
      setResendHint(t.resendOk);
    } catch {
      setResendHint(t.resendOk);
    } finally {
      setBusy(false);
    }
  }

  const langSwitch = (
    <LangSwitch lang={lang} onChange={setLang} ariaLabel={t.langAria} />
  );

  if (checkEmail) {
    return (
      <div className="kid auth-kid" data-testid="auth-page">
        <div className="auth-shell">
          <div className="auth-card" data-testid="auth-check-email">
            <div className="auth-card-head">
              {langSwitch}
            </div>
            <div className="auth-logo">
              <Link to="/">
                <img src={logo} alt="Story R Us" />
              </Link>
            </div>
            <SiteBackNav />
            <h1>{t.checkTitle}</h1>
            <p className="auth-lead">{t.checkLead}</p>
            <p className="auth-lead auth-check-hint">{t.checkHint}</p>
            {resendHint && (
              <p className="auth-lead auth-check-hint" data-testid="auth-resend-hint">
                {resendHint}
              </p>
            )}
            <p className="auth-foot">
              <button
                type="button"
                disabled={busy || !email.trim()}
                onClick={() => void onResend()}
                data-testid="auth-resend-verify"
              >
                {busy ? t.resendBusy : t.resend}
              </button>
            </p>
            <p className="auth-foot">
              <Link to={`/entrar?next=${encodeURIComponent(next)}`} data-testid="auth-switch">
                {t.switchToLogin}
              </Link>
            </p>
            <p className="auth-foot">
              <Link to="/" data-testid="auth-back">
                {t.back}
              </Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isSignup = mode === "signup";

  return (
    <div
      className={`kid auth-kid${isSignup ? " auth-kid-full" : ""}`}
      data-testid="auth-page"
    >
      <div className={`auth-shell${isSignup ? " auth-shell-full" : ""}`}>
        <div className={`auth-card${isSignup ? " auth-card-full" : ""}`}>
          {isSignup ? (
            <div className="auth-topbar">
              <Link to="/" className="auth-logo-inline">
                <img src={logo} alt="Story R Us" />
              </Link>
              {langSwitch}
            </div>
          ) : (
            <>
              <div className="auth-card-head">{langSwitch}</div>
              <div className="auth-logo">
                <Link to="/">
                  <img src={logo} alt="Story R Us" />
                </Link>
              </div>
            </>
          )}
          <SiteBackNav />
          <header className={isSignup ? "auth-hero" : undefined}>
            <h1>{isSignup ? t.signupTitle : t.loginTitle}</h1>
            <p className="auth-lead">{isSignup ? t.signupLead : t.loginLead}</p>
          </header>
          <form
            className={`auth-form${isSignup ? " auth-form-full" : ""}`}
            onSubmit={onSubmit}
            data-testid="auth-form"
          >
            {isSignup && (
              <p className="auth-section-title auth-span-all">{t.accountSection}</p>
            )}
            {isSignup && (
              <label className="auth-span-all">
                {t.fullName}
                <input
                  type="text"
                  required
                  autoComplete="name"
                  value={signup.full_name}
                  onChange={(e) => setSignup({ ...signup, full_name: e.target.value })}
                  data-testid="auth-full-name"
                />
              </label>
            )}
            <label>
              {t.email}
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="auth-email"
              />
            </label>
            {isSignup && (
              <label>
                {t.phone}
                <input
                  type="tel"
                  required
                  minLength={8}
                  autoComplete="tel"
                  placeholder={region.phonePlaceholder}
                  value={signup.phone}
                  onChange={(e) => setSignup({ ...signup, phone: e.target.value })}
                  data-testid="auth-phone"
                />
              </label>
            )}
            <PasswordField
              label={t.password}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              testId="auth-password"
              lang={lang}
            />
            {isSignup && (
              <>
                <PasswordField
                  label={t.passwordConfirm}
                  value={signup.password_confirm}
                  onChange={(e) => setSignup({ ...signup, password_confirm: e.target.value })}
                  autoComplete="new-password"
                  testId="auth-password-confirm"
                  lang={lang}
                />
                <p className="auth-section-title auth-span-all">{t.addressSection}</p>
                <div
                  className={`auth-address auth-span-all${isUsLayout ? " auth-address-us" : ""}`}
                  data-testid="auth-address"
                >
                  <label className="auth-span-all">
                    {t.country}
                    <select
                      required
                      value={signup.country}
                      onChange={(e) => onCountryChange(e.target.value)}
                      data-testid="auth-country"
                      autoComplete="country"
                    >
                      {COUNTRY_GROUPS.map((group) => (
                        <optgroup key={group.id} label={group.label[lang]}>
                          {group.countries.map((c) => (
                            <option key={c.code} value={c.code}>
                              {c.label[lang]}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </label>
                  {isUsLayout ? (
                    <>
                      <label className="auth-span-all">
                        {t.street}
                        <input
                          type="text"
                          required
                          autoComplete="street-address"
                          placeholder={region.streetPlaceholder[lang]}
                          value={signup.street}
                          onChange={(e) => setSignup({ ...signup, street: e.target.value })}
                          data-testid="auth-street"
                        />
                      </label>
                      <label>
                        {region.numberLabel[lang]}
                        <input
                          type="text"
                          required={region.numberRequired}
                          placeholder={region.numberPlaceholder[lang]}
                          value={signup.number}
                          onChange={(e) => setSignup({ ...signup, number: e.target.value })}
                          data-testid="auth-number"
                        />
                      </label>
                      <label>
                        {t.city}
                        <input
                          type="text"
                          required
                          autoComplete="address-level2"
                          value={signup.city}
                          onChange={(e) => setSignup({ ...signup, city: e.target.value })}
                          data-testid="auth-city"
                        />
                      </label>
                      <label>
                        {region.stateLabel[lang]}
                        {region.stateOptions ? (
                          <select
                            required
                            value={signup.state}
                            onChange={(e) => setSignup({ ...signup, state: e.target.value })}
                            data-testid="auth-state"
                            autoComplete="address-level1"
                          >
                            <option value="" disabled>
                              —
                            </option>
                            {region.stateOptions.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            required
                            autoComplete="address-level1"
                            value={signup.state}
                            onChange={(e) => setSignup({ ...signup, state: e.target.value })}
                            data-testid="auth-state"
                          />
                        )}
                      </label>
                      <label>
                        {region.postalLabel[lang]}
                        <input
                          type="text"
                          required
                          minLength={signup.country === "US" ? 5 : 2}
                          maxLength={signup.country === "US" ? 5 : 16}
                          inputMode={signup.country === "US" ? "numeric" : undefined}
                          autoComplete="postal-code"
                          placeholder={region.postalPlaceholder}
                          value={signup.postal_code}
                          onChange={(e) => onPostalCodeChange(e.target.value)}
                          data-testid="auth-postal-code"
                        />
                        {postalLookupOn && cepStatusText(cepStatus, t) && (
                          <span
                            className={`auth-cep-status is-${cepStatus}`}
                            data-testid="auth-cep-status"
                            role="status"
                          >
                            {cepStatusText(cepStatus, t)}
                          </span>
                        )}
                      </label>
                    </>
                  ) : (
                    <>
                      <label>
                        {region.postalLabel[lang]}
                        <input
                          type="text"
                          required
                          minLength={signup.country === "BR" ? 8 : 2}
                          maxLength={signup.country === "BR" ? 9 : 16}
                          inputMode={signup.country === "BR" ? "numeric" : undefined}
                          autoComplete="postal-code"
                          placeholder={region.postalPlaceholder}
                          value={signup.postal_code}
                          onChange={(e) => onPostalCodeChange(e.target.value)}
                          data-testid="auth-postal-code"
                        />
                        {postalLookupOn && cepStatusText(cepStatus, t) && (
                          <span
                            className={`auth-cep-status is-${cepStatus}`}
                            data-testid="auth-cep-status"
                            role="status"
                          >
                            {cepStatusText(cepStatus, t)}
                          </span>
                        )}
                      </label>
                      <label>
                        {t.city}
                        <input
                          type="text"
                          required
                          autoComplete="address-level2"
                          value={signup.city}
                          onChange={(e) => setSignup({ ...signup, city: e.target.value })}
                          data-testid="auth-city"
                        />
                      </label>
                      <label className="auth-span-all">
                        {t.street}
                        <input
                          type="text"
                          required
                          autoComplete="street-address"
                          placeholder={region.streetPlaceholder[lang]}
                          value={signup.street}
                          onChange={(e) => setSignup({ ...signup, street: e.target.value })}
                          data-testid="auth-street"
                        />
                      </label>
                      <label>
                        {region.numberLabel[lang]}
                        <input
                          type="text"
                          required={region.numberRequired}
                          placeholder={region.numberPlaceholder[lang]}
                          value={signup.number}
                          onChange={(e) => setSignup({ ...signup, number: e.target.value })}
                          data-testid="auth-number"
                        />
                      </label>
                      {region.showComplement && (
                        <label>
                          {region.complementLabel[lang]}
                          <input
                            type="text"
                            value={signup.complement}
                            onChange={(e) => setSignup({ ...signup, complement: e.target.value })}
                            data-testid="auth-complement"
                          />
                        </label>
                      )}
                      {region.showDistrict && (
                        <label>
                          {region.districtLabel[lang]}
                          <input
                            type="text"
                            required={region.districtRequired}
                            value={signup.district}
                            onChange={(e) => setSignup({ ...signup, district: e.target.value })}
                            data-testid="auth-district"
                          />
                        </label>
                      )}
                      <label>
                        {region.stateLabel[lang]}
                        {region.stateOptions ? (
                          <select
                            required
                            value={signup.state}
                            onChange={(e) => setSignup({ ...signup, state: e.target.value })}
                            data-testid="auth-state"
                            autoComplete="address-level1"
                          >
                            <option value="" disabled>
                              —
                            </option>
                            {region.stateOptions.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            required
                            minLength={1}
                            maxLength={80}
                            autoComplete="address-level1"
                            value={signup.state}
                            onChange={(e) =>
                              setSignup({
                                ...signup,
                                state:
                                  signup.country === "BR"
                                    ? e.target.value.toUpperCase()
                                    : e.target.value,
                              })
                            }
                            data-testid="auth-state"
                          />
                        )}
                      </label>
                    </>
                  )}
                </div>
                <label className="auth-terms auth-span-all">
                  <input
                    type="checkbox"
                    checked={signup.accept_terms}
                    onChange={(e) => setSignup({ ...signup, accept_terms: e.target.checked })}
                    data-testid="auth-accept-terms"
                  />
                  <span>
                    {t.acceptTerms}{" "}
                    <Link to="/termos" target="_blank" rel="noreferrer">
                      {t.terms}
                    </Link>{" "}
                    {t.termsAnd}{" "}
                    <Link to="/privacidade" target="_blank" rel="noreferrer">
                      {t.privacy}
                    </Link>
                    .
                  </span>
                </label>
              </>
            )}
            {error && (
              <p className="auth-error auth-span-all" role="alert" data-testid="auth-error">
                {error}
              </p>
            )}
            <button
              type="submit"
              className="kbtn kbtn-primary auth-cta auth-span-all"
              disabled={busy}
              data-testid="auth-submit"
            >
              {busy ? t.busy : mode === "login" ? t.loginSubmit : t.signupSubmit}
            </button>
          </form>
          {isSignup ? (
            <div className="auth-foot-row">
              <Link to={altHref} data-testid="auth-switch">
                {t.switchToLogin}
              </Link>
              <Link to="/" data-testid="auth-back">
                {t.back}
              </Link>
            </div>
          ) : (
            <>
              <p className="auth-foot">
                <Link
                  to={`/esqueci-senha?next=${encodeURIComponent(next)}`}
                  data-testid="auth-forgot"
                >
                  {t.forgotPassword}
                </Link>
              </p>
              <p className="auth-foot">
                <Link to={altHref} data-testid="auth-switch">
                  {t.switchToSignup}
                </Link>
              </p>
              <p className="auth-foot">
                <Link to="/" data-testid="auth-back">
                  {t.back}
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
