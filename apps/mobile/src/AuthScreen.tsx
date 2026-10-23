import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useAuth } from "@clerk/expo";
import { useSignIn, useSignUp } from "@clerk/expo/legacy";
import { api, getToken, type MeUser } from "./api";

function needsProfile(me: MeUser): boolean {
  return (
    !me.terms_accepted_at ||
    !me.adult_confirmed_at ||
    !me.full_name?.trim() ||
    !me.street?.trim() ||
    !me.city?.trim() ||
    !me.phone?.trim()
  );
}

/** Conta no Clerk e endereço de envio na nossa API. */
export function AuthScreen({ onAuthed }: { onAuthed: () => void }) {
  if (!process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return (
      <View style={s.wrap}>
        <Text style={s.title}>Entrar</Text>
        <Text style={s.muted}>Login indisponível até a chave do Clerk estar configurada.</Text>
      </View>
    );
  }
  return <ClerkAuth onAuthed={onAuthed} />;
}

function ClerkAuth({ onAuthed }: { onAuthed: () => void }) {
  const { isLoaded: authLoaded, isSignedIn } = useAuth();
  const { signIn, setActive, isLoaded: signInLoaded } = useSignIn();
  const { signUp, setActive: setActiveSignUp, isLoaded: signUpLoaded } = useSignUp();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [awaitingCode, setAwaitingCode] = useState(false);
  const [me, setMe] = useState<MeUser | null>(null);
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [street, setStreet] = useState("");
  const [number, setNumber] = useState("");
  const [complement, setComplement] = useState("");
  const [district, setDistrict] = useState("");
  const [city, setCity] = useState("");
  const [stateUf, setStateUf] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [confirmAdult, setConfirmAdult] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const signedIn = Boolean(isSignedIn || getToken());

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    api.me()
      .then((user) => {
        if (!cancelled) setMe(user);
      })
      .catch(() => {
        if (!cancelled) setMe(null);
      });
    return () => {
      cancelled = true;
    };
  }, [signedIn]);

  useEffect(() => {
    if (me && me.email_verified && !needsProfile(me)) onAuthed();
  }, [me, onAuthed]);

  async function submitAuth() {
    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") {
        if (!signUp) throw new Error("Cadastro indisponível.");
        await signUp.create({ emailAddress: email.trim(), password });
        await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
        setAwaitingCode(true);
        return;
      }
      if (!signIn) throw new Error("Login indisponível.");
      const result = await signIn.create({ identifier: email.trim(), password });
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        return;
      }
      setError("Confirme o e-mail para entrar.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitCode() {
    setBusy(true);
    setError(null);
    try {
      if (!signUp) throw new Error("Cadastro indisponível.");
      const result = await signUp.attemptEmailAddressVerification({ code: code.trim() });
      if (result.status === "complete") {
        await setActiveSignUp({ session: result.createdSessionId });
        setAwaitingCode(false);
        return;
      }
      setError("Código inválido. Tente de novo.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitProfile() {
    if (!confirmAdult) {
      setError("Confirme que você tem 18 anos ou mais.");
      return;
    }
    if (!acceptTerms) {
      setError("Aceite os termos e a política de privacidade.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await api.updateMe({
        full_name: fullName.trim(),
        phone: phone.trim(),
        postal_code: postalCode.trim(),
        street: street.trim(),
        number: number.trim(),
        complement: complement.trim() || null,
        district: district.trim() || null,
        city: city.trim(),
        state: stateUf.trim().toUpperCase(),
        country: "BR",
        accept_terms: true,
        confirm_adult: true,
      });
      setMe(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!authLoaded || !signInLoaded || !signUpLoaded) {
    return (
      <View style={s.wrap}>
        <ActivityIndicator color="#5b8cff" />
      </View>
    );
  }

  if (awaitingCode) {
    return (
      <View style={s.wrap}>
        <Text style={s.title}>Confirme o e-mail</Text>
        <Text style={s.muted}>Digite o código enviado para {email.trim()}.</Text>
        <TextInput
          style={s.input}
          placeholder="Código"
          placeholderTextColor="#93a0bd"
          keyboardType="number-pad"
          value={code}
          onChangeText={setCode}
        />
        {error ? <Text style={s.error}>{error}</Text> : null}
        <Pressable style={s.btn} disabled={busy} onPress={() => void submitCode()}>
          <Text style={s.btnText}>{busy ? "Aguarde…" : "Confirmar"}</Text>
        </Pressable>
      </View>
    );
  }

  if (signedIn && me && !me.email_verified) {
    return (
      <View style={s.wrap}>
        <Text style={s.title}>Confirme o e-mail</Text>
        <Text style={s.muted}>A conta fica liberada depois que o Clerk confirmar {me.email}.</Text>
      </View>
    );
  }

  if (signedIn && me && needsProfile(me)) {
    return (
      <ScrollView contentContainerStyle={s.wrap} keyboardShouldPersistTaps="handled">
        <Text style={s.title}>Endereço de envio</Text>
        <Text style={s.muted}>O livro impresso usa este endereço. A senha fica no Clerk.</Text>
        <TextInput style={s.input} placeholder="Nome completo" placeholderTextColor="#93a0bd" value={fullName} onChangeText={setFullName} />
        <TextInput style={s.input} placeholder="Telefone / WhatsApp" placeholderTextColor="#93a0bd" keyboardType="phone-pad" value={phone} onChangeText={setPhone} />
        <TextInput style={s.input} placeholder="CEP" placeholderTextColor="#93a0bd" keyboardType="number-pad" value={postalCode} onChangeText={setPostalCode} />
        <TextInput style={s.input} placeholder="Rua" placeholderTextColor="#93a0bd" value={street} onChangeText={setStreet} />
        <TextInput style={s.input} placeholder="Número" placeholderTextColor="#93a0bd" value={number} onChangeText={setNumber} />
        <TextInput style={s.input} placeholder="Complemento" placeholderTextColor="#93a0bd" value={complement} onChangeText={setComplement} />
        <TextInput style={s.input} placeholder="Bairro" placeholderTextColor="#93a0bd" value={district} onChangeText={setDistrict} />
        <TextInput style={s.input} placeholder="Cidade" placeholderTextColor="#93a0bd" value={city} onChangeText={setCity} />
        <TextInput style={s.input} placeholder="Estado" placeholderTextColor="#93a0bd" autoCapitalize="characters" value={stateUf} onChangeText={setStateUf} />
        <Pressable style={s.check} onPress={() => setConfirmAdult((v) => !v)}>
          <Text style={s.muted}>
            {confirmAdult ? "☑" : "☐"} Tenho 18 anos ou mais. Esta conta é minha, como pai, mãe ou responsável. Menores de 13 anos não podem criar conta.
          </Text>
        </Pressable>
        <Pressable style={s.check} onPress={() => setAcceptTerms((v) => !v)}>
          <Text style={s.muted}>{acceptTerms ? "☑" : "☐"} Aceito os termos e a política de privacidade.</Text>
        </Pressable>
        {error ? <Text style={s.error}>{error}</Text> : null}
        <Pressable style={s.btn} disabled={busy} onPress={() => void submitProfile()}>
          <Text style={s.btnText}>{busy ? "Aguarde…" : "Salvar e continuar"}</Text>
        </Pressable>
      </ScrollView>
    );
  }

  if (signedIn && !me) {
    return (
      <View style={s.wrap}>
        <ActivityIndicator color="#5b8cff" />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={s.wrap} keyboardShouldPersistTaps="handled">
      <Text style={s.title}>{mode === "signup" ? "Criar conta" : "Entrar"}</Text>
      <Text style={s.muted}>É preciso ter uma conta para criar livros personalizados.</Text>
      <TextInput
        style={s.input}
        placeholder="E-mail"
        placeholderTextColor="#93a0bd"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={s.input}
        placeholder="Senha (mín. 8)"
        placeholderTextColor="#93a0bd"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      {error ? <Text style={s.error}>{error}</Text> : null}
      <Pressable style={s.btn} disabled={busy} onPress={() => void submitAuth()}>
        <Text style={s.btnText}>{busy ? "Aguarde…" : mode === "signup" ? "Criar conta" : "Entrar"}</Text>
      </Pressable>
      <Pressable onPress={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); }}>
        <Text style={s.link}>{mode === "login" ? "Criar conta" : "Já tenho conta"}</Text>
      </Pressable>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { padding: 24, gap: 12 },
  title: { color: "#f1f5f9", fontSize: 28, fontWeight: "700" },
  muted: { color: "#93a0bd", lineHeight: 20 },
  input: {
    backgroundColor: "#1a2030",
    color: "#f1f5f9",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  btn: { backgroundColor: "#5b8cff", borderRadius: 8, paddingVertical: 14, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700" },
  link: { color: "#5b8cff", textAlign: "center" },
  error: { color: "#f87171" },
  check: { paddingVertical: 4 },
});
