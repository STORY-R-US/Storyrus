import { useId, useState, type ChangeEventHandler } from "react";

type Props = {
  label: string;
  value: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
  autoComplete?: string;
  required?: boolean;
  minLength?: number;
  testId?: string;
  /** Idioma curto para o aria-label do botão. */
  lang?: "pt" | "en" | "es";
};

const SHOW: Record<NonNullable<Props["lang"]>, string> = {
  pt: "Mostrar Senha",
  en: "Show Password",
  es: "Mostrar Contraseña",
};

const HIDE: Record<NonNullable<Props["lang"]>, string> = {
  pt: "Ocultar Senha",
  en: "Hide Password",
  es: "Ocultar Contraseña",
};

function IcEyeOpen() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="2.6" />
    </svg>
  );
}

function IcEyeOff() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M3 3l18 18" />
      <path d="M10.6 10.7a2.6 2.6 0 0 0 3.7 3.7" />
      <path d="M9.4 5.7A9.7 9.7 0 0 1 12 5.5C18 5.5 21.5 12 21.5 12a17 17 0 0 1-3.2 4.1" />
      <path d="M6.1 6.3C3.9 7.9 2.5 12 2.5 12S6 18.5 12 18.5c1.2 0 2.3-.2 3.3-.5" />
    </svg>
  );
}

/** Campo de senha com botão olho para mostrar/ocultar. */
export function PasswordField({
  label,
  value,
  onChange,
  autoComplete = "current-password",
  required = true,
  minLength = 8,
  testId,
  lang = "pt",
}: Props) {
  const [visible, setVisible] = useState(false);
  const reactId = useId();
  const inputId = testId ? `${testId}-input` : `password-${reactId}`;
  const toggleLabel = visible ? HIDE[lang] : SHOW[lang];

  return (
    <label htmlFor={inputId}>
      {label}
      <span className="auth-password-wrap">
        <input
          id={inputId}
          type={visible ? "text" : "password"}
          required={required}
          minLength={minLength}
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          data-testid={testId}
        />
        <button
          type="button"
          className="auth-password-toggle"
          aria-label={toggleLabel}
          aria-pressed={visible}
          data-testid={testId ? `${testId}-toggle` : "password-toggle"}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? <IcEyeOff /> : <IcEyeOpen />}
        </button>
      </span>
    </label>
  );
}
