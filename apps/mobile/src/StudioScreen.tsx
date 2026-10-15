import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { api } from "./api";
import { THEMES, THEME_GROUP_LABEL, themeLabel } from "./themes";
import { VoicePanel } from "./VoicePanel";
import type { Job, Project, ProjectAssets, StudioStep, Theme, ThemeGroup, UserVoice } from "./types";

const STEPS: { key: StudioStep; label: string }[] = [
  { key: "avatar", label: "Gerar personagem" },
  { key: "story", label: "Escrever história" },
  { key: "ebook", label: "Montar ebook" },
  { key: "video", label: "Gerar vídeo" },
  { key: "narrated-video", label: "Vídeo narrado" },
];

const DOT: Record<string, string> = {
  PENDING: "#facc15",
  RUNNING: "#5b8cff",
  DONE: "#34d399",
  FAILED: "#f87171",
};

const GROUPS: ThemeGroup[] = ["aventura", "datas", "educativo"];

export function StudioScreen({
  onLogout,
  bootError,
}: {
  onLogout: () => void | Promise<void>;
  bootError?: string | null;
}) {
  const [project, setProject] = useState<Project | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [assets, setAssets] = useState<ProjectAssets | null>(null);
  const [photoUploaded, setPhotoUploaded] = useState(false);
  const [mediaConsent, setMediaConsent] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState<Theme[]>(["adventure"]);
  const [childName, setChildName] = useState("");
  const [childAge, setChildAge] = useState("");
  const [dedication, setDedication] = useState("");
  const [voices, setVoices] = useState<UserVoice[]>([]);
  const [customVoiceAvailable, setCustomVoiceAvailable] = useState(false);
  const [selectedVoiceId, setSelectedVoiceId] = useState("");
  const [voiceName, setVoiceName] = useState("Minha voz");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const theme = selectedThemes[0] ?? "adventure";
  const extraTheme = selectedThemes[1];
  const characterApproved = !!project?.character_approved_at;
  const bookApproved = !!project?.book_approved_at;
  const printRequested = !!project?.print_requested_at;

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

  const refreshAssets = useCallback(async (projectId: string) => {
    try {
      setAssets(await api.getAssets(projectId));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshVoices();
  }, [refreshVoices]);

  useEffect(() => {
    if (!project) return;
    const active = jobs.some((j) => j.status === "PENDING" || j.status === "RUNNING");
    if (!active) {
      if (poll.current) clearInterval(poll.current);
      void refreshAssets(project.id);
      return;
    }
    poll.current = setInterval(async () => {
      try {
        const [p, js] = await Promise.all([api.getProject(project.id), api.listJobs(project.id)]);
        setProject(p);
        setJobs(js);
        const stillActive = js.some((j) => j.status === "PENDING" || j.status === "RUNNING");
        if (!stillActive) void refreshAssets(project.id);
      } catch {
        /* ignore */
      }
    }, 2500);
    return () => {
      if (poll.current) clearInterval(poll.current);
    };
  }, [project, jobs, refreshAssets]);

  function toggleTheme(id: Theme) {
    setSelectedThemes((prev) => {
      if (prev.includes(id)) {
        const next = prev.filter((t) => t !== id);
        return next.length ? next : prev;
      }
      if (prev.length >= 2) return [prev[0], id];
      return [...prev, id];
    });
  }

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const ageNum = childAge.trim() ? Number(childAge) : undefined;
      const p = await api.createProject(
        theme,
        extraTheme,
        childName,
        dedication,
        Number.isFinite(ageNum) ? ageNum : undefined,
      );
      setProject(p);
      setJobs([]);
      setAssets(null);
      setPhotoUploaded(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function pickAndUpload() {
    if (!project) return;
    if (!mediaConsent) {
      setError("Marque o consentimento antes de enviar a foto.");
      return;
    }
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
    });
    if (res.canceled) return;
    setPhotoUploaded(false);
    setBusy(true);
    setError(null);
    try {
      const asset = res.assets[0];
      const ext = asset.uri.split(".").pop() || "jpg";
      const u = await api.requestPhotoUpload(project.id, asset.mimeType || "image/jpeg", ext);
      await api.uploadToSignedUrl(u.upload_url, asset.uri, asset.mimeType || "image/jpeg");
      setPhotoUploaded(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runStep(step: StudioStep) {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      let body: Record<string, unknown> = {};
      if (step === "narrated-video" && selectedVoiceId) body = { voice_id: selectedVoiceId };
      await api.startStep(project.id, step, body);
      setJobs(await api.listJobs(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approveCharacter() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.approveCharacter(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approveBook() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.approveBook(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function requestPrint() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      setProject(await api.requestPrint(project.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function onVoiceUploaded(voice: UserVoice) {
    await refreshVoices();
    setSelectedVoiceId(voice.id);
  }

  async function removeSelectedVoice() {
    if (!selectedVoiceId) return;
    setError(null);
    try {
      await api.deleteVoice(selectedVoiceId);
      await refreshVoices();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function openUrl(url: string | null | undefined) {
    if (!url) return;
    void Linking.openURL(url);
  }

  function resetProject() {
    setProject(null);
    setJobs([]);
    setAssets(null);
    setPhotoUploaded(false);
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={{ padding: 20, gap: 12 }}>
      <View style={s.header}>
        <Text style={s.brand}>Story R Us</Text>
        <View style={{ flex: 1 }} />
        <Pressable onPress={() => void onLogout()}>
          <Text style={s.link}>  Sair</Text>
        </Pressable>
      </View>

      {bootError && <Text style={s.error}>{bootError}</Text>}
      {error && <Text style={s.error}>{error}</Text>}

      {!project ? (
        <View style={s.card}>
          <Text style={s.h2}>Novo projeto</Text>
          <Text style={s.muted}>
            Escolha até 2 temas. O 1º define a aventura; o 2º só acrescenta um aprendizado.
          </Text>

          {GROUPS.map((group) => (
            <View key={group} style={{ gap: 8 }}>
              <Text style={s.group}>{THEME_GROUP_LABEL[group]}</Text>
              <View style={s.chips}>
                {THEMES.filter((t) => t.group === group).map((t) => {
                  const on = selectedThemes.includes(t.id);
                  const ord = selectedThemes.indexOf(t.id);
                  return (
                    <Pressable
                      key={t.id}
                      style={[s.chip, on && s.chipOn]}
                      onPress={() => toggleTheme(t.id)}
                    >
                      <Text style={s.chipText}>
                        {t.emoji} {t.label}
                        {ord === 0 ? " ·1" : ord === 1 ? " ·2" : ""}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          ))}

          <Text style={s.h3}>Nome, idade e dedicatória</Text>
          <TextInput
            style={s.input}
            value={childName}
            onChangeText={setChildName}
            placeholder="Nome da criança"
            placeholderTextColor="#6b7a9a"
          />
          <TextInput
            style={s.input}
            value={childAge}
            onChangeText={setChildAge}
            placeholder="Idade (ex.: 5)"
            placeholderTextColor="#6b7a9a"
            keyboardType="number-pad"
          />
          <TextInput
            style={[s.input, { minHeight: 64 }]}
            value={dedication}
            onChangeText={setDedication}
            placeholder="Dedicatória (página 2)"
            placeholderTextColor="#6b7a9a"
            multiline
          />

          <Pressable style={s.btn} onPress={start} disabled={busy}>
            <Text style={s.btnText}>Criar projeto</Text>
          </Pressable>
        </View>
      ) : (
        <View style={s.card}>
          <Text style={s.h2}>Projeto</Text>
          <Text style={s.muted}>
            Tema: {themeLabel(project.theme)}
            {project.extra_theme ? ` + ${themeLabel(project.extra_theme)}` : ""}
            {project.child_name ? ` · ${project.child_name}` : ""}
            {" · "}Status: {project.status}
          </Text>

          <Pressable
            style={[s.consent, mediaConsent && s.consentOn]}
            onPress={() => setMediaConsent((v) => !v)}
          >
            <Text style={s.consentMark}>{mediaConsent ? "✓" : "○"}</Text>
            <Text style={s.muted}>
              Sou o responsável legal e autorizo o uso desta foto (e voz, se clonada) só para criar
              este livro.
            </Text>
          </Pressable>

          <Pressable
            style={[s.btnAlt, (!mediaConsent || busy) && s.disabled]}
            onPress={pickAndUpload}
            disabled={busy || !mediaConsent}
          >
            <Text style={s.btnText}>{photoUploaded ? "Foto enviada ✓" : "Enviar foto"}</Text>
          </Pressable>

          {STEPS.map((st) => {
            const needPhoto = st.key === "avatar" && !photoUploaded;
            const needChar =
              (st.key === "ebook" || st.key === "video" || st.key === "narrated-video") &&
              !characterApproved;
            const disabled = busy || needPhoto || needChar;
            return (
              <Pressable
                key={st.key}
                style={[s.btn, disabled && s.disabled]}
                onPress={() => runStep(st.key)}
                disabled={disabled}
              >
                <Text style={s.btnText}>{st.label}</Text>
              </Pressable>
            );
          })}
          {!characterApproved && photoUploaded ? (
            <Text style={s.hint}>Aprove o personagem antes do ebook / vídeos.</Text>
          ) : null}

          <VoicePanel
            busy={busy}
            mediaConsent={mediaConsent}
            voices={voices}
            customVoiceAvailable={customVoiceAvailable}
            selectedVoiceId={selectedVoiceId}
            voiceName={voiceName}
            onSelectVoice={setSelectedVoiceId}
            onVoiceName={setVoiceName}
            onUploaded={onVoiceUploaded}
            onRemove={() => void removeSelectedVoice()}
            onError={setError}
          />

          {jobs.map((j) => (
            <View key={j.id} style={s.job}>
              <View style={[s.dot, { backgroundColor: DOT[j.status] }]} />
              <Text style={s.jtype}>{j.type}</Text>
              <Text style={s.muted}>{j.status}</Text>
              {j.error ? <Text style={s.error}>{j.error}</Text> : null}
            </View>
          ))}

          {busy && <ActivityIndicator color="#5b8cff" />}

          {(assets?.character_url || assets?.realistic_url) && (
            <View style={s.block}>
              <Text style={s.h3}>Personagem</Text>
              <Image
                source={{ uri: (assets.character_url || assets.realistic_url)! }}
                style={s.preview}
                resizeMode="cover"
              />
              {characterApproved ? (
                <Text style={s.ok}>Personagem aprovado ✓</Text>
              ) : (
                <Pressable style={s.btnAlt} onPress={() => void approveCharacter()} disabled={busy}>
                  <Text style={s.btnText}>Aprovar personagem</Text>
                </Pressable>
              )}
            </View>
          )}

          {(assets?.ebook_url || project.ebook_url || (assets?.page_images?.length ?? 0) > 0) && (
            <View style={s.block}>
              <Text style={s.h3}>Livro</Text>
              {assets?.page_images?.slice(0, 4).map((u, i) => (
                <Image key={i} source={{ uri: u }} style={s.pageThumb} resizeMode="cover" />
              ))}
              {(assets?.ebook_url || project.ebook_url) && (
                <Pressable onPress={() => openUrl(assets?.ebook_url || project.ebook_url)}>
                  <Text style={s.link}>Abrir ebook PDF</Text>
                </Pressable>
              )}
              {bookApproved ? (
                <Text style={s.ok}>Livro aprovado ✓</Text>
              ) : (
                <Pressable
                  style={[s.btnAlt, !(assets?.ebook_url || project.ebook_url) && s.disabled]}
                  onPress={() => void approveBook()}
                  disabled={busy || !(assets?.ebook_url || project.ebook_url)}
                >
                  <Text style={s.btnText}>Aprovar livro</Text>
                </Pressable>
              )}
              {bookApproved &&
                (printRequested ? (
                  <Text style={s.ok}>Impressão solicitada ✓</Text>
                ) : (
                  <Pressable style={s.btnAlt} onPress={() => void requestPrint()} disabled={busy}>
                    <Text style={s.btnText}>Pedir impressão</Text>
                  </Pressable>
                ))}
            </View>
          )}

          {project.story_text ? <Text style={s.story}>{project.story_text}</Text> : null}
          {(assets?.video_url || project.video_url) && (
            <Pressable onPress={() => openUrl(assets?.video_url || project.video_url)}>
              <Text style={s.ok}>Abrir vídeo</Text>
            </Pressable>
          )}
          {(assets?.narrated_video_url || project.narrated_video_url) && (
            <Pressable
              onPress={() => openUrl(assets?.narrated_video_url || project.narrated_video_url)}
            >
              <Text style={s.ok}>Abrir vídeo narrado</Text>
            </Pressable>
          )}

          <Pressable onPress={resetProject}>
            <Text style={s.link}>← Novo projeto</Text>
          </Pressable>
        </View>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#0f1320" },
  header: { flexDirection: "row", alignItems: "center", paddingVertical: 8 },
  brand: { color: "#e8ecf5", fontWeight: "700", fontSize: 18 },
  card: {
    backgroundColor: "#182032",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 16,
    padding: 18,
    gap: 10,
  },
  h2: { color: "#e8ecf5", fontSize: 18, fontWeight: "700" },
  h3: { color: "#e8ecf5", fontSize: 15, fontWeight: "700", marginTop: 4 },
  group: { color: "#c5d0ea", fontSize: 13, fontWeight: "600" },
  muted: { color: "#93a0bd", flexShrink: 1 },
  hint: { color: "#facc15", fontSize: 13 },
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
  input: {
    backgroundColor: "#0d1322",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#e8ecf5",
  },
  consent: {
    flexDirection: "row",
    gap: 10,
    alignItems: "flex-start",
    backgroundColor: "#0d1322",
    borderColor: "#2a3550",
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
  },
  consentOn: { borderColor: "#5b8cff" },
  consentMark: { color: "#5b8cff", fontWeight: "700", width: 18 },
  btn: { backgroundColor: "#5b8cff", borderRadius: 8, padding: 12, alignItems: "center" },
  btnAlt: { backgroundColor: "#334066", borderRadius: 8, padding: 12, alignItems: "center" },
  disabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontWeight: "700" },
  link: { color: "#5b8cff" },
  job: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 4, flexWrap: "wrap" },
  dot: { width: 10, height: 10, borderRadius: 5 },
  jtype: { color: "#e8ecf5", fontWeight: "600", minWidth: 90 },
  story: { color: "#e8ecf5", backgroundColor: "#0d1322", padding: 12, borderRadius: 8 },
  ok: { color: "#34d399" },
  error: { color: "#f87171" },
  block: { gap: 8, marginTop: 4 },
  preview: { width: "100%", height: 220, borderRadius: 12, backgroundColor: "#0d1322" },
  pageThumb: { width: 96, height: 96, borderRadius: 8, backgroundColor: "#0d1322" },
});
