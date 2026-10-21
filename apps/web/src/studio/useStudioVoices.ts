import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { api } from "../api";
import type { UserVoice } from "../types";

type Args = {
  isDemo: boolean;
  mediaConsent: boolean;
  setError: Dispatch<SetStateAction<string | null>>;
  consentError: string;
  defaultVoiceName: string;
};

export function useStudioVoices({
  isDemo,
  mediaConsent,
  setError,
  consentError,
  defaultVoiceName,
}: Args) {
  const [voices, setVoices] = useState<UserVoice[]>([]);
  const [customVoiceAvailable, setCustomVoiceAvailable] = useState(false);
  const [selectedVoiceId, setSelectedVoiceId] = useState("");
  const [voiceName, setVoiceName] = useState(defaultVoiceName);
  const [voiceUploading, setVoiceUploading] = useState(false);

  useEffect(() => {
    setVoiceName((prev) => {
      // Only sync placeholder default when user hasn't customized it.
      if (!prev || prev === "Minha voz" || prev === "My voice" || prev === "Mi voz") {
        return defaultVoiceName;
      }
      return prev;
    });
  }, [defaultVoiceName]);

  const refreshVoices = useCallback(async () => {
    try {
      const data = await api.listVoices();
      setVoices(data.items);
      setCustomVoiceAvailable(data.custom_voice_available);
      setSelectedVoiceId((prev) => {
        if (prev && data.items.some((v) => v.id === prev)) return prev;
        const def = data.items.find((v) => v.is_default);
        return def?.id || data.items[0]?.id || "";
      });
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshVoices();
  }, [refreshVoices]);

  async function onVoiceFile(file: File | null) {
    if (!file || isDemo) return;
    if (!mediaConsent) {
      setError(consentError);
      return;
    }
    setVoiceUploading(true);
    setError(null);
    try {
      const voice = await api.uploadVoice(
        file,
        voiceName.trim() || defaultVoiceName,
        voices.length === 0,
      );
      await refreshVoices();
      setSelectedVoiceId(voice.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setVoiceUploading(false);
    }
  }

  async function removeSelectedVoice() {
    if (!selectedVoiceId || isDemo) return;
    setError(null);
    try {
      await api.deleteVoice(selectedVoiceId);
      await refreshVoices();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return {
    voices,
    customVoiceAvailable,
    selectedVoiceId,
    setSelectedVoiceId,
    voiceName,
    setVoiceName,
    voiceUploading,
    onVoiceFile,
    removeSelectedVoice,
  };
}
