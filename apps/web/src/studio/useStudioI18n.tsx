import { createContext, useContext, useMemo } from "react";
import {
  LANGS,
  type Lang,
  readStoredLang,
  useResolvedLang,
} from "../i18n/lang";
import { studioCopy, type StudioCopy } from "./i18n";

type StudioLangValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: StudioCopy;
  langs: Lang[];
};

const StudioLangContext = createContext<StudioLangValue | null>(null);

export function useStudioLangState(): StudioLangValue {
  const [lang, setLang] = useResolvedLang();
  const t = useMemo(() => studioCopy(lang), [lang]);
  return { lang, setLang, t, langs: LANGS };
}

export function StudioLangProvider({
  value,
  children,
}: {
  value: StudioLangValue;
  children: React.ReactNode;
}) {
  return <StudioLangContext.Provider value={value}>{children}</StudioLangContext.Provider>;
}

export function useStudioI18n(): StudioLangValue {
  const ctx = useContext(StudioLangContext);
  if (!ctx) {
    // Safe fallback for isolated unit tests (e.g. ProgressList alone).
    const lang = readStoredLang("pt");
    return {
      lang,
      setLang: () => undefined,
      t: studioCopy(lang),
      langs: LANGS,
    };
  }
  return ctx;
}
