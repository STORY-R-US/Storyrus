import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { api } from "./api";
import type { UserVoice } from "./types";

type Props = {
  busy: boolean;
  mediaConsent: boolean;
  voices: UserVoice[];
  customVoiceAvailable: boolean;
  selectedVoiceId: string;
  voiceName: string;
  onSelectVoice: (id: string) => void;
  onVoiceName: (name: string) => void;
  onUploaded: (voice: UserVoice) => void | Promise<void>;
  onRemove: () => void;
  onError: (msg: string) => void;
};

/** Seleção / clone de voz para vídeo narrado (paridade com VoiceNarrationPanel do web). */
export function VoicePanel({
  busy,
  mediaConsent,
  voices,
  customVoiceAvailable,
  selectedVoiceId,
  voiceName,
  onSelectVoice,
  onVoiceName,
  onUploaded,
  onRemove,
  onError,
}: Props) {
  const [uploading, setUploading] = useState(false);

  async function pickAndUpload() {
    if (!mediaConsent) {
      onError("Marque o consentimento antes de enviar áudio.");
      return;
    }
    const res = await DocumentPicker.getDocumentAsync({
      type: ["audio/*"],
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets?.[0]) return;
    const asset = res.assets[0];
    setUploading(true);
    try {
      const voice = await api.uploadVoice(
        asset.uri,
        voiceName.trim() || "Minha voz",
        asset.mimeType || "audio/mpeg",
        voices.length === 0,
      );
      await onUploaded(voice);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <View style={s.block}>
      <Text style={s.h3}>Voz da narração</Text>
      {!customVoiceAvailable ? (
        <Text style={s.muted}>Clone de voz indisponível neste ambiente.</Text>
      ) : (
        <>
          <Text style={s.muted}>
            Envie um áudio curto (mp3/m4a/wav) para narrar o vídeo com a sua voz.
          </Text>
          <TextInput
            style={s.input}
            value={voiceName}
            onChangeText={onVoiceName}
            placeholder="Nome da voz"
            placeholderTextColor="#6b7a9a"
            editable={!busy && !uploading}
          />
          <Pressable
            style={[s.btnAlt, (busy || uploading || !mediaConsent) && s.disabled]}
            onPress={() => void pickAndUpload()}
            disabled={busy || uploading || !mediaConsent}
          >
            <Text style={s.btnText}>{uploading ? "Clonando…" : "Enviar áudio"}</Text>
          </Pressable>
          {voices.length > 0 && (
            <View style={s.chips}>
              <Pressable
                style={[s.chip, !selectedVoiceId && s.chipOn]}
                onPress={() => onSelectVoice("")}
                disabled={busy}
              >
                <Text style={s.chipText}>Automática</Text>
              </Pressable>
              {voices.map((v) => (
                <Pressable
                  key={v.id}
                  style={[s.chip, selectedVoiceId === v.id && s.chipOn]}
                  onPress={() => onSelectVoice(v.id)}
                  disabled={busy}
                >
                  <Text style={s.chipText}>
                    {v.name}
                    {v.is_default ? " ★" : ""}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}
          {selectedVoiceId ? (
            <Pressable onPress={onRemove} disabled={busy}>
              <Text style={s.link}>Remover voz selecionada</Text>
            </Pressable>
          ) : null}
        </>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  block: { gap: 8, marginTop: 4 },
  h3: { color: "#e8ecf5", fontSize: 15, fontWeight: "700" },
  muted: { color: "#93a0bd", fontSize: 13 },
  input: {
    backgroundColor: "#0d1322",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#e8ecf5",
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    backgroundColor: "#0d1322",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  chipOn: { backgroundColor: "#5b8cff", borderColor: "#5b8cff" },
  chipText: { color: "#e8ecf5", fontSize: 13 },
  btnAlt: { backgroundColor: "#334066", borderRadius: 8, padding: 12, alignItems: "center" },
  disabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontWeight: "700" },
  link: { color: "#5b8cff" },
});
