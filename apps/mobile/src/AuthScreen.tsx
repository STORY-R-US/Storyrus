import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api, type SignupPayload } from "./api";

/** Login/signup obrigatório antes do estúdio. */
export function AuthScreen({
  onAuthed,
  initialMode = "login",
}: {
  onAuthed: () => void;
  initialMode?: "login" | "signup";
}) {
  const [mode, setMode] = useState<"login" | "signup">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
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
  const [checkEmail, setCheckEmail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") {
        if (password !== passwordConfirm) {
          setError("As senhas não coincidem.");
          return;
        }
        if (!acceptTerms) {
          setError("Aceite os termos e a política de privacidade.");
          return;
        }
        const payload: SignupPayload = {
          email: email.trim(),
          password,
          password_confirm: passwordConfirm,
          full_name: fullName.trim(),
          phone: phone.trim(),
          postal_code: postalCode.trim(),
          street: street.trim(),
          number: number.trim(),
          complement: complement.trim() || null,
          district: district.trim(),
          city: city.trim(),
          state: stateUf.trim().toUpperCase(),
          accept_terms: true,
        };
        await api.signup(payload);
        setCheckEmail(true);
        return;
      }
      await api.login(email.trim(), password);
      onAuthed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (checkEmail) {
    return (
      <View style={s.wrap}>
        <Text style={s.title}>Verifique seu e-mail</Text>
        <Text style={s.muted}>
          Enviamos um link de confirmação. Ative a conta e depois entre com e-mail e senha.
        </Text>
        <Pressable
          onPress={() => {
            setCheckEmail(false);
            setMode("login");
          }}
        >
          <Text style={s.link}>Já confirmei — entrar</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={s.wrap} keyboardShouldPersistTaps="handled">
      <Text style={s.title}>{mode === "signup" ? "Criar conta" : "Entrar"}</Text>
      <Text style={s.muted}>
        É preciso ter uma conta para criar livros personalizados.
      </Text>

      {mode === "signup" && (
        <TextInput
          style={s.input}
          placeholder="Nome completo"
          placeholderTextColor="#93a0bd"
          value={fullName}
          onChangeText={setFullName}
        />
      )}

      <TextInput
        style={s.input}
        placeholder="E-mail"
        placeholderTextColor="#93a0bd"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />

      {mode === "signup" && (
        <TextInput
          style={s.input}
          placeholder="Telefone / WhatsApp"
          placeholderTextColor="#93a0bd"
          keyboardType="phone-pad"
          value={phone}
          onChangeText={setPhone}
        />
      )}

      <TextInput
        style={s.input}
        placeholder="Senha (mín. 8)"
        placeholderTextColor="#93a0bd"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {mode === "signup" && (
        <>
          <TextInput
            style={s.input}
            placeholder="Confirmar senha"
            placeholderTextColor="#93a0bd"
            secureTextEntry
            value={passwordConfirm}
            onChangeText={setPasswordConfirm}
          />
          <TextInput
            style={s.input}
            placeholder="CEP"
            placeholderTextColor="#93a0bd"
            keyboardType="number-pad"
            value={postalCode}
            onChangeText={setPostalCode}
          />
          <TextInput
            style={s.input}
            placeholder="Rua"
            placeholderTextColor="#93a0bd"
            value={street}
            onChangeText={setStreet}
          />
          <TextInput
            style={s.input}
            placeholder="Número"
            placeholderTextColor="#93a0bd"
            value={number}
            onChangeText={setNumber}
          />
          <TextInput
            style={s.input}
            placeholder="Complemento (opcional)"
            placeholderTextColor="#93a0bd"
            value={complement}
            onChangeText={setComplement}
          />
          <TextInput
            style={s.input}
            placeholder="Bairro"
            placeholderTextColor="#93a0bd"
            value={district}
            onChangeText={setDistrict}
          />
          <TextInput
            style={s.input}
            placeholder="Cidade"
            placeholderTextColor="#93a0bd"
            value={city}
            onChangeText={setCity}
          />
          <TextInput
            style={s.input}
            placeholder="UF"
            placeholderTextColor="#93a0bd"
            autoCapitalize="characters"
            maxLength={2}
            value={stateUf}
            onChangeText={(v) => setStateUf(v.toUpperCase())}
          />
          <Pressable style={s.termsRow} onPress={() => setAcceptTerms(!acceptTerms)}>
            <View style={[s.checkbox, acceptTerms && s.checkboxOn]} />
            <Text style={s.termsText}>Aceito os termos de uso e a política de privacidade</Text>
          </Pressable>
        </>
      )}

      {error && <Text style={s.error}>{error}</Text>}

      <Pressable style={s.btn} onPress={submit} disabled={busy}>
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={s.btnText}>{mode === "signup" ? "Criar conta" : "Entrar"}</Text>
        )}
      </Pressable>

      <Pressable
        onPress={() => {
          setMode(mode === "signup" ? "login" : "signup");
          setCheckEmail(false);
          setError(null);
        }}
      >
        <Text style={s.link}>{mode === "signup" ? "Já tenho conta" : "Criar uma conta"}</Text>
      </Pressable>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { flexGrow: 1, justifyContent: "center", padding: 24, gap: 10, backgroundColor: "#0f1320" },
  title: { color: "#e8ecf5", fontSize: 24, fontWeight: "700" },
  muted: { color: "#93a0bd", marginBottom: 12 },
  input: {
    backgroundColor: "#0d1322",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    color: "#e8ecf5",
  },
  termsRow: { flexDirection: "row", alignItems: "flex-start", gap: 10, marginTop: 4 },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "#5b8cff",
    marginTop: 2,
  },
  checkboxOn: { backgroundColor: "#5b8cff" },
  termsText: { color: "#93a0bd", flex: 1, lineHeight: 20 },
  btn: { backgroundColor: "#5b8cff", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 6 },
  btnText: { color: "#fff", fontWeight: "700" },
  link: { color: "#5b8cff", textAlign: "center", marginTop: 12 },
  error: { color: "#f87171" },
});
