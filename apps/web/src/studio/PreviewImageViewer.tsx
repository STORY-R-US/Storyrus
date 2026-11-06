import { useEffect, useId, useRef, useState } from "react";

const COPY = {
  pt: { close: "Fechar", details: "Ver detalhes", fit: "Ajustar à tela" },
  en: { close: "Close", details: "View details", fit: "Fit to screen" },
  es: { close: "Cerrar", details: "Ver detalles", fit: "Ajustar a la pantalla" },
};

export function PreviewImageViewer({ src, title, lang, onClose }: {
  src: string; title: string; lang: "pt" | "en" | "es"; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [details, setDetails] = useState(false);
  const t = COPY[lang];
  useEffect(() => {
    const element = dialog.current!;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = overflow;
    };
  }, []);
  return (
    <dialog ref={dialog} className="studio-image-viewer" aria-labelledby={titleId}
      onClose={() => { if (!dialog.current?.open) onClose(); }} onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom) event.currentTarget.close();
      }}>
      <header className="studio-image-viewer-toolbar">
        <h2 id={titleId}>{title}</h2>
        <button type="button" aria-pressed={details} onClick={() => setDetails(!details)}>{details ? t.fit : t.details}</button>
        <button type="button" onClick={() => dialog.current?.close()}>{t.close}</button>
      </header>
      <div className={`studio-image-viewer-canvas${details ? " is-details" : ""}`}>
        <img src={src} alt={title} />
      </div>
    </dialog>
  );
}
