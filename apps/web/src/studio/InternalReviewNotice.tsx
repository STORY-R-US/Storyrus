const copy = {
  pt: ["Sua prévia está em revisão interna", "Estamos conferindo os detalhes antes da entrega. Seu projeto está salvo; você não precisa alterar os textos, reenviar a foto ou repetir a criação. A prévia aparecerá aqui quando a revisão for concluída."],
  en: ["Your preview is under internal review", "We are checking the details before delivery. Your project is saved; you do not need to change the text, upload the photo again or restart creation. Your preview will appear here when the review is complete."],
  es: ["Tu vista previa está en revisión interna", "Estamos revisando los detalles antes de la entrega. Tu proyecto está guardado; no necesitas cambiar los textos, subir la foto de nuevo ni repetir la creación. La vista previa aparecerá aquí al finalizar la revisión."],
};
export function InternalReviewNotice({ lang }: { lang: "pt" | "en" | "es" }) {
  const [title, detail] = copy[lang];
  return <section role="status" aria-live="polite" data-testid="studio-internal-review"><h3>{title}</h3><p>{detail}</p></section>;
}
