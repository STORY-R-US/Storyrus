import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider, useAuth } from "@clerk/react";
import { enUS, esES, ptBR } from "@clerk/localizations";
import { Root } from "./Root";
import { markClerkPresent, setClerkGetToken, setClerkSignOut } from "./api";
import { warmBackend } from "./backendConnection";
import "./styles.css";
import "./studio.css";

function clerkLocalization() {
  let lang = "pt";
  try {
    lang = localStorage.getItem("lang") || "pt";
  } catch {
    /* storage indisponível */
  }
  if (lang === "en") return enUS;
  if (lang === "es") return esES;
  return ptBR;
}

function ClerkBridge() {
  markClerkPresent();
  const { getToken, signOut, isLoaded } = useAuth();
  useEffect(() => {
    if (!isLoaded) return;
    setClerkGetToken((opts) => getToken(opts));
    setClerkSignOut(() => signOut());
    return () => {
      setClerkGetToken(null);
      setClerkSignOut(null);
    };
  }, [getToken, signOut, isLoaded]);
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

void warmBackend().catch(() => { /* a próxima ação pode tentar novamente */ });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {clerkKey ? (
      <ClerkProvider publishableKey={clerkKey} localization={clerkLocalization()}>
        <AppTree />
      </ClerkProvider>
    ) : (
      <Root />
    )}
  </React.StrictMode>,
);
