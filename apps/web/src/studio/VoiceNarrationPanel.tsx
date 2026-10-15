import { useStudioI18n } from "./useStudioI18n";

type Props = {
  customVoiceAvailable: boolean;
  voiceName: string;
  setVoiceName: (v: string) => void;
  voiceUploading: boolean;
  locked: boolean;
  mediaConsent: boolean;
  onVoiceFile: (file: File | null) => void;
  voices: { id: string; name: string; is_default: boolean }[];
  selectedVoiceId: string;
  setSelectedVoiceId: (id: string) => void;
  removeSelectedVoice: () => void;
};

/** Narration voice clone / select UI (look preserved from Studio monolith). */
export function VoiceNarrationPanel({
  customVoiceAvailable,
  voiceName,
  setVoiceName,
  voiceUploading,
  locked,
  mediaConsent,
  onVoiceFile,
  voices,
  selectedVoiceId,
  setSelectedVoiceId,
  removeSelectedVoice,
}: Props) {
  const { t } = useStudioI18n();
  return (
    <div className="result-block" style={{ marginBottom: 16 }} role="region" aria-labelledby="studio-voice-heading">
      <h3 className="field-label" id="studio-voice-heading">
        {t.voiceTitle}
      </h3>
      {!customVoiceAvailable ? (
        <p className="muted">{t.voiceUnavailable}</p>
      ) : (
        <>
          <p className="muted" style={{ marginBottom: 10 }}>
            {t.voiceHint}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
            <input
              type="text"
              value={voiceName}
              onChange={(e) => setVoiceName(e.target.value)}
              placeholder={t.voiceNamePh}
              aria-label={t.ariaVoiceName}
            />
            <label className="btn" style={{ cursor: voiceUploading ? "wait" : "pointer" }}>
              {voiceUploading ? t.cloning : t.sendAudio}
              <input
                type="file"
                accept="audio/mpeg,audio/wav,audio/mp4,audio/x-m4a,audio/webm,audio/ogg,.mp3,.wav,.m4a,.webm,.ogg"
                hidden
                disabled={voiceUploading || locked || !mediaConsent}
                aria-label={t.ariaSendAudioClone}
                onChange={(e) => onVoiceFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>
          {voices.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              <select
                value={selectedVoiceId}
                onChange={(e) => setSelectedVoiceId(e.target.value)}
                disabled={locked}
                aria-label={t.ariaSelectVoice}
              >
                <option value="">{t.voiceAuto}</option>
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                    {v.is_default ? t.voiceDefault : ""}
                  </option>
                ))}
              </select>
              {selectedVoiceId && (
                <button type="button" disabled={locked} onClick={removeSelectedVoice}>
                  {t.removeVoice}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
