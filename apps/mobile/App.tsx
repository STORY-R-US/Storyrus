import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { AuthScreen } from "./src/AuthScreen";
import { StudioScreen } from "./src/StudioScreen";
import { api, getToken, hydrateToken, logout, ensureSession, isSessionRejected } from "./src/api";

/** Conta obrigatória: login/signup antes do estúdio. */
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
        if (!cancelled) setAuthed(!me.is_guest && me.email_verified);
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

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0f1320" },
  boot: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 20 },
  error: { color: "#f1f5f9", textAlign: "center" },
  retry: { backgroundColor: "#5b8cff", borderRadius: 8, paddingVertical: 12, paddingHorizontal: 20 },
  retryText: { color: "#fff", fontWeight: "600" },
});
