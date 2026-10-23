import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { ClerkProvider, useAuth } from "@clerk/expo";
import { AuthScreen } from "./src/AuthScreen";
import { StudioScreen } from "./src/StudioScreen";
import { tokenCache } from "./src/clerkTokenCache";
import { api, getToken, hydrateToken, logout, ensureSession, isSessionRejected, setClerkGetToken, setClerkSignOut } from "./src/api";

function needsAccount(me: {
  is_guest: boolean;
  email_verified: boolean;
  terms_accepted_at?: string | null;
  full_name?: string | null;
  street?: string | null;
  city?: string | null;
  phone?: string | null;
}): boolean {
  return me.is_guest || !me.email_verified || !me.terms_accepted_at || !me.full_name?.trim() || !me.street?.trim() || !me.city?.trim() || !me.phone?.trim();
}

function ClerkSession() {
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

/** Conta obrigatória: sessão do Clerk antes do estúdio. */
export default function App() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [bootAttempt, setBootAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    setBootError(null);
    (async () => {
      try {
        await hydrateToken();
        if (!getToken()) {
          if (!cancelled) setAuthed(false);
          return;
        }
        await ensureSession();
        const me = await api.me();
        if (cancelled) return;
        if (me.is_guest) {
          logout();
          setAuthed(false);
          return;
        }
        setAuthed(!needsAccount(me));
      } catch (error) {
        if (cancelled) return;
        if (isSessionRejected(error)) {
          logout();
          setAuthed(false);
        } else {
          setBootError("Não foi possível conectar agora. Verifique sua conexão e tente novamente.");
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, [bootAttempt]);

  return (
    <SafeAreaView style={s.root}>
      <StatusBar style="light" />
      {!ready ? (
        <View style={s.boot}>
          <ActivityIndicator color="#5b8cff" size="large" />
        </View>
      ) : bootError ? (
        <View style={s.boot}>
          <Text style={s.error} accessibilityRole="alert">{bootError}</Text>
          <Pressable style={s.retry} accessibilityRole="button" onPress={() => setBootAttempt((value) => value + 1)}>
            <Text style={s.retryText}>Tentar novamente</Text>
          </Pressable>
        </View>
      ) : !authed ? (
        <AuthScreen onAuthed={() => { setAuthed(true); setBootError(null); }} />
      ) : (
        <StudioScreen
          bootError={bootError}
          onLogout={async () => {
            logout();
            setAuthed(false);
            setBootError(null);
          }}
        />
      )}
    </SafeAreaView>
  );
}

export function Root() {
  const key = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key) return <App />;
  return (
    <ClerkProvider publishableKey={key} tokenCache={tokenCache}>
      <ClerkSession />
      <App />
    </ClerkProvider>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0f1320" },
  boot: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 20 },
  error: { color: "#f1f5f9", textAlign: "center" },
  retry: { backgroundColor: "#5b8cff", borderRadius: 8, paddingVertical: 12, paddingHorizontal: 20 },
  retryText: { color: "#fff", fontWeight: "600" },
});
