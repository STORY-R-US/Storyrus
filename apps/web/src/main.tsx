import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { enUS, esES, ptBR } from "@clerk/localizations";
import { Root } from "./Root";
import { markClerkPresent, setClerkGetToken, setClerkSignOut } from "./api";
import { warmBackend } from "./backendConnection";
import "./styles.css";
import "./studio.css";
import { useResolvedLang } from "./i18n/lang";

// The bundled Spanish locale omits the combined sign-in/sign-up heading.
const clerkSpanish = {
  ...esES,
  signIn: {
    ...esES.signIn,
    start: {
      ...esES.signIn?.start,
      titleCombined: "Continuar en {{applicationName}}",
      subtitleCombined: "Inicia sesión o crea una cuenta para continuar.",
    },
  },
};

function clerkLocalization(lang: string) {
  if (lang === "en") return enUS;
  if (lang === "es") return clerkSpanish;
  return ptBR;
}

function ClerkBridge() {
  markClerkPresent();
  const { getToken, signOut, isLoaded, isSignedIn } = useAuth();
  useEffect(() => {
    if (!isLoaded) return;
    setClerkGetToken((opts) => getToken(opts));
    setClerkSignOut(() => signOut());
  }, [getToken, signOut, isLoaded, isSignedIn]);
  return null;
}

function AppTree() {
  return (
    <>
      <ClerkBridge />
      <Root />
    </>
  );
}

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function LocalizedApp() {
  const [lang] = useResolvedLang();
  return clerkKey ? (
    <ClerkProvider publishableKey={clerkKey} localization={clerkLocalization(lang)}>
      <AppTree />
    </ClerkProvider>
  ) : <Root />;
}

void warmBackend().catch(() => { /* a próxima ação pode tentar novamente */ });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LocalizedApp />
  </React.StrictMode>,
);
