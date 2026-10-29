import { FormEvent, useEffect, useMemo, useState } from "react";
import { SignIn, SignUp, useAuth } from "@clerk/react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import logo from "./assets/logo.png";
import { api, getToken, type MeUser } from "./api";
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
    profileLead: string;
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
    confirmAdult: string;
    mustBeAdult: string;
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
    signupTitle: "Endereço de entrega",
    loginLead: "A sessão fica salva neste navegador. Na próxima visita você continua dentro, sem pedir o código de novo.",
    signupLead: "Primeira vez: Google, Apple, Facebook, Microsoft ou o código do e-mail. Quem já tem conta usa Entrar.",
    profileLead: "A conta já está criada. Estes dados ficam salvos para o envio do livro.",
    accountSection: "Quem recebe",
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
    signupSubmit: "Salvar e continuar",
    busy: "Aguarde…",
    switchToSignup: "Criar Uma Conta",
    switchToLogin: "Já Tenho Conta",
    forgotPassword: "Esqueci A Senha",
    back: "Voltar Ao Início",
    checkTitle: "Confirme o e-mail",
    checkLead: "O código chegou no e-mail. Digite esse código na tela de entrar para abrir a conta.",
    checkHint: "Não achou? Olhe o spam. O assunto começa com o código da Story R Us.",
    passwordMismatch: "As senhas não coincidem.",
    mustAcceptTerms: "Aceite os termos e a política de privacidade.",
    confirmAdult:
      "Declaro ter 18 anos ou mais. Esta conta é minha, como pai, mãe ou responsável. Menores de 13 anos não podem criar conta.",
    mustBeAdult: "Confirme que você tem 18 anos ou mais.",
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
    signupTitle: "Shipping address",
    loginLead: "This browser keeps you signed in. Next time you come back, the code is not asked again.",
    signupLead: "First time: Google, Apple, Facebook, Microsoft, or the email code. If you already have an account, use Log In.",
    profileLead: "The account is already created. These details stay saved for shipping.",
    accountSection: "Who receives it",
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
    signupSubmit: "Save and continue",
    busy: "Please wait…",
    switchToSignup: "Create An Account",
    switchToLogin: "I Already Have An Account",
    forgotPassword: "Forgot Password",
    back: "Back To Home",
    checkTitle: "Confirm your email",
    checkLead: "The code is in your email. Enter it on the sign-in screen to open the account.",
    checkHint: "Can't find it? Check spam. The subject starts with your Story R Us code.",
    passwordMismatch: "Passwords do not match.",
    mustAcceptTerms: "Please accept the terms and privacy policy.",
    confirmAdult:
      "I am 18 or older. This account is mine, as a parent or guardian. Children under 13 may not create an account.",
    mustBeAdult: "Confirm that you are 18 or older.",
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
    signupTitle: "Dirección de envío",
    loginLead: "La sesión queda en este navegador. La próxima visita no vuelve a pedir el código.",
    signupLead: "Primera vez: Google, Apple, Facebook, Microsoft o el código del correo. Quien ya tiene cuenta usa Entrar.",
    profileLead: "La cuenta ya está creada. Estos datos quedan guardados para el envío.",
    accountSection: "Quién recibe",
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
    signupSubmit: "Guardar y continuar",
    busy: "Espera…",
    switchToSignup: "Crear Una Cuenta",
    switchToLogin: "Ya Tengo Cuenta",
    forgotPassword: "Olvidé La Contraseña",
    back: "Volver Al Inicio",
    checkTitle: "Confirma tu correo",
    checkLead: "El código llegó al correo. Escríbelo en la pantalla de entrar para abrir la cuenta.",
    checkHint: "¿No lo ves? Revisa spam. El asunto empieza con el código de Story R Us.",
    passwordMismatch: "Las contraseñas no coinciden.",
    mustAcceptTerms: "Acepta los términos y la política de privacidad.",
    confirmAdult:
      "Declaro tener 18 años o más. Esta cuenta es mía, como padre, madre o tutor. Los menores de 13 años no pueden crear una cuenta.",
    mustBeAdult: "Confirma que tienes 18 años o más.",
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

/** Endereço e termos continuam nossos; o Clerk não guarda isso. */
export function needsShippingProfile(me: {
  terms_accepted_at?: string | null;
  adult_confirmed_at?: string | null;
  full_name?: string | null;
  street?: string | null;
  city?: string | null;
  phone?: string | null;
}): boolean {
  return (
    !me.terms_accepted_at ||
    !me.adult_confirmed_at ||
    !me.full_name?.trim() ||
    !me.street?.trim() ||
    !me.city?.trim() ||
    !me.phone?.trim()
  );
}

/** Conta pronta para o estúdio, convidado legado, ou perfil ainda incompleto. */
export function accountAccess(me: {
  is_guest: boolean;
  email_verified: boolean;
  terms_accepted_at?: string | null;
  adult_confirmed_at?: string | null;
  full_name?: string | null;
  street?: string | null;
  city?: string | null;
  phone?: string | null;
}): "ok" | "guest" | "need-account" {
  if (me.is_guest) return "guest";
  if (!me.email_verified || needsShippingProfile(me)) return "need-account";
  return "ok";
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
    accept_terms: false,
    confirm_adult: false,
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
  if (!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY) {
    return <AuthBody mode={mode} isLoaded isSignedIn={false} />;
  }
  return <AuthClerk mode={mode} />;
}

function AuthClerk({ mode }: { mode: AuthMode }) {
  const { isLoaded, isSignedIn } = useAuth();
  return <AuthBody mode={mode} isLoaded={Boolean(isLoaded)} isSignedIn={Boolean(isSignedIn)} />;
}

function AuthBody({
  mode,
  isLoaded,
  isSignedIn,
}: {
  mode: AuthMode;
  isLoaded: boolean;
  isSignedIn: boolean;
}) {
  usePageMeta(staticPageMeta(mode === "login" ? "/entrar" : "/cadastro"));
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = useMemo(() => safeNextPath(params.get("next")), [params]);
  const [lang, setLangBase] = useResolvedLang();
  const t = COPY[lang];
  const [signup, setSignup] = useState(() => emptySignup(lang));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [me, setMe] = useState<MeUser | null>(null);
  const [meState, setMeState] = useState<"idle" | "loading" | "ready">("idle");

  const region = regionProfile(signup.country);
  const isUsLayout = region.layout === "us";
  const postalLookupOn = supportsPostalLookup(signup.country);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn && !getToken()) {
      setMe(null);
      setMeState("ready");
      return;
    }
    let cancelled = false;
    setMeState("loading");
    api.me()
      .then((user) => {
        if (!cancelled) {
          setMe(user);
          setMeState("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMe(null);
          setMeState("ready");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);
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

  useEffect(() => {
    setSignup((prev) => {
      const stillDefault = !prev.street && !prev.city && !prev.postal_code && !prev.state;
      if (!stillDefault) return prev;
      const nextCountry = defaultCountry(lang);
      if (prev.country === nextCountry) return prev;
      return { ...prev, country: nextCountry, state: "" };
    });
  }, [lang]);

  useEffect(() => {
    if (!me?.full_name && !me?.street) return;
    setSignup((prev) => {
      if (prev.full_name || prev.street) return prev;
      return {
        ...prev,
        full_name: me.full_name || "",
        phone: me.phone || "",
        country: me.country || prev.country,
        postal_code: me.postal_code || "",
        street: me.street || "",
        number: me.number || "",
        complement: me.complement || "",
        district: me.district || "",
        city: me.city || "",
        state: me.state || "",
        accept_terms: Boolean(me.terms_accepted_at),
      };
    });
  }, [me]);

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
      if (!signup.confirm_adult) {
        setError(t.mustBeAdult);
        return;
      }
      if (!signup.accept_terms) {
        setError(t.mustAcceptTerms);
        return;
      }
      await api.updateMe({
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
        confirm_adult: true,
      });
      navigate(next, { replace: true });
    } catch (err) {
      setError(friendlyAuthError((err as Error).message || ""));
    } finally {
      setBusy(false);
    }
  }

  const langSwitch = (
    <LangSwitch lang={lang} onChange={setLang} ariaLabel={t.langAria} />
  );

  if (!isLoaded || meState !== "ready") {
    return (
      <div className="kid auth-kid" data-testid="auth-page">
        <div className="auth-shell">
          <div className="auth-card">
            <p className="auth-lead" data-testid="auth-loading">{t.busy}</p>
          </div>
        </div>
      </div>
    );
  }

  const signedIn = Boolean(isSignedIn || getToken());
  if (!signedIn) {
    const clerkReady = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);
    return (
      <div className="kid auth-kid" data-testid="auth-page">
        <div className="auth-shell auth-shell-clerk">
          <div className="auth-card auth-card-clerk">
            <div className="auth-card-head">{langSwitch}</div>
            <div className="auth-logo">
              <Link to="/">
                <img src={logo} alt="Story R Us" />
              </Link>
            </div>
            <SiteBackNav className="site-back-nav-center" />
            <p className="auth-lead" data-testid="auth-clerk-hint">
              {mode === "login" ? t.loginLead : t.signupLead}
            </p>
            {clerkReady ? (
              mode === "login" ? (
                <SignIn
                  routing="path"
                  path="/entrar"
                  signUpUrl={`/cadastro?next=${encodeURIComponent(next)}`}
                  fallbackRedirectUrl={`/entrar?next=${encodeURIComponent(next)}`}
                  forceRedirectUrl={`/entrar?next=${encodeURIComponent(next)}`}
                />
              ) : (
                <SignUp
                  routing="path"
                  path="/cadastro"
                  signInUrl={`/entrar?next=${encodeURIComponent(next)}`}
                  fallbackRedirectUrl={`/cadastro?next=${encodeURIComponent(next)}`}
                  forceRedirectUrl={`/cadastro?next=${encodeURIComponent(next)}`}
                />
              )
            ) : (
              <p className="auth-lead" data-testid="auth-clerk-missing">
                {lang === "en"
                  ? "Sign-in is unavailable until Clerk is configured."
                  : lang === "es"
                    ? "El inicio de sesión no está disponible hasta configurar Clerk."
                    : "O login fica indisponível até a chave do Clerk estar configurada."}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (me && !me.email_verified) {
    return (
      <div className="kid auth-kid" data-testid="auth-page">
        <div className="auth-shell">
          <div className="auth-card" data-testid="auth-check-email">
            <div className="auth-card-head">{langSwitch}</div>
            <div className="auth-logo">
              <Link to="/">
                <img src={logo} alt="Story R Us" />
              </Link>
            </div>
            <SiteBackNav />
            <h1>{t.checkTitle}</h1>
            <p className="auth-lead">{t.checkLead}</p>
            <p className="auth-lead auth-check-hint">{t.checkHint}</p>
            <p className="auth-foot">
              <Link to="/" data-testid="auth-back">{t.back}</Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (me && !needsShippingProfile(me)) {
    return <Navigate to={next} replace />;
  }

  const isSignup = true;

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
          <SiteBackNav className="site-back-nav-center" />
          <header className={isSignup ? "auth-hero" : undefined}>
            <h1>{isSignup ? t.signupTitle : t.loginTitle}</h1>
            <p className="auth-lead">{t.profileLead}</p>
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
            {isSignup && (
              <label className="auth-span-all">
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
            {isSignup && (
              <>
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
                    checked={signup.confirm_adult}
                    onChange={(e) => setSignup({ ...signup, confirm_adult: e.target.checked })}
                    data-testid="auth-confirm-adult"
                  />
                  <span>{t.confirmAdult}</span>
                </label>
                <label className="auth-terms auth-span-all">
                  <input
                    type="checkbox"
                    checked={signup.accept_terms}
                    onChange={(e) => setSignup({ ...signup, accept_terms: e.target.checked })}
                    data-testid="auth-accept-terms"
                  />
                  <span>
                    {t.acceptTerms}{" "}
                    <Link to={lang === "en" ? "/terms" : "/termos"} target="_blank" rel="noreferrer">
                      {t.terms}
                    </Link>{" "}
                    {t.termsAnd}{" "}
                    <Link
                      to={lang === "en" ? "/privacy" : "/privacidade"}
                      target="_blank"
                      rel="noreferrer"
                    >
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
              {busy ? t.busy : t.signupSubmit}
            </button>
          </form>
          <div className="auth-foot-row">
            <Link to="/" data-testid="auth-back">
              {t.back}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
