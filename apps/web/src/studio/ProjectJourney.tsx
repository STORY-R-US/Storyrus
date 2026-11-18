import type { Lang } from "../i18n/lang";
import type { Project } from "../types";

const COPY = {
  pt: {
    label: "A Criação Do Seu Livro", step: "Etapa", of: "de", done: "Livro Aprovado",
    steps: ["Prévia E História", "Pedido E Criação", "Revisão E Entrega"],
    preview: ["Uma História Começa A Ganhar Vida.", "Leia a história com calma. Aprove ou peça ajustes em qualquer página."],
    images: ["As imagens da sua prévia", "Confira as imagens. Se gostar, siga para a história completa."],
    retry: ["Sua Aprovação Vem Primeiro.", "Vamos preparar uma nova prévia com IA para você revisar. O pedido só continuará após a sua confirmação."],
    order: ["O Próximo Capítulo É Seu Livro.", "Escolha o formato, confira o endereço e finalize o pedido."],
    storyReview: ["História Aprovada.", "Confira o resumo e continue para o pedido."],
    payment: ["Acompanhe Seu Pedido.", "Assim que o pagamento for confirmado, começamos o livro completo."],
    creating: ["Seu Livro Está Ganhando Forma.", "As páginas aparecem aqui conforme ficam prontas."],
    review: ["Cada Página, Do Seu Jeito.", "Confira o livro completo, peça ajustes se quiser e aprove."],
    approved: ["Uma História Pronta Para Guardar.", "Seu livro foi aprovado e segue para impressão."],
  },
  en: {
    label: "Your Book's Journey", step: "Step", of: "of", done: "Book Approved",
    steps: ["Preview And Story", "Order And Creation", "Review And Delivery"],
    preview: ["A Story Is Coming To Life.", "Read the story at your own pace. Approve it or ask for changes on any page."],
    images: ["Your preview images", "Check the images. If you like them, move on to the full story."],
    retry: ["Your Approval Comes First.", "We will prepare a new AI preview for your review. The order will only continue after your confirmation."],
    order: ["The Next Chapter Is Your Book.", "Choose the format, check the address and complete the order."],
    storyReview: ["Story Approved.", "Check the summary and continue to the order."],
    payment: ["Follow Your Order.", "Once payment is confirmed, we start the complete book."],
    creating: ["Your Book Is Taking Shape.", "Pages appear here as they become ready."],
    review: ["Every Page, Your Way.", "Review the complete book, ask for changes if you want, and approve it."],
    approved: ["A Story Ready To Treasure.", "Your book is approved and on its way to print."],
  },
  es: {
    label: "La Creación De Tu Libro", step: "Paso", of: "de", done: "Libro Aprobado",
    steps: ["Vista Previa E Historia", "Pedido Y Creación", "Revisión Y Entrega"],
    preview: ["Una Historia Empieza A Cobrar Vida.", "Lee la historia con calma. Apruébala o pide ajustes en cualquier página."],
    images: ["Las imágenes de tu vista previa", "Revisa las imágenes. Si te gustan, sigue con la historia completa."],
    retry: ["Tu Aprobación Es Lo Primero.", "Prepararemos una nueva vista previa con IA para que la revises. El pedido solo continuará después de tu confirmación."],
    order: ["El Próximo Capítulo Es Tu Libro.", "Elige el formato, revisa la dirección y finaliza el pedido."],
    storyReview: ["Historia Aprobada.", "Revisa el resumen y continúa con el pedido."],
    payment: ["Sigue Tu Pedido.", "Cuando se confirme el pago, empezamos el libro completo."],
    creating: ["Tu Libro Está Tomando Forma.", "Las páginas aparecen aquí a medida que están listas."],
    review: ["Cada Página, A Tu Manera.", "Revisa el libro completo, pide ajustes si quieres y apruébalo."],
    approved: ["Una Historia Lista Para Guardar.", "Tu libro está aprobado y va a impresión."],
  },
};

export function ProjectJourney({ project, lang }: { project: Project; lang: Lang }) {
  const t = COPY[lang];
  const stage = project.book_profile?.stage;
  const flow = project.purchase_flow;
  const validPreview = !project.book_profile?.credits_fallback;
  const approved = validPreview && Boolean(flow?.preview_approved_at) && Boolean(project.book_approved_at);
  const ready = validPreview && Boolean(flow?.preview_approved_at) && (Boolean(flow?.full_book_ready_at) || stage === "book_ready");
  const creating = validPreview && Boolean(flow?.preview_approved_at) && (flow?.stage === "generating_book" || (project.book_profile?.current_page ?? 0) > 0
    || ["avatar_ready", "avatar_approved", "page_ready"].includes(stage || ""));
  const ordering = validPreview && Boolean(flow?.preview_approved_at);
  const storyReview = validPreview && stage === "story_approved" && !flow?.preview_approved_at;
  const current = approved || ready ? 2 : creating || ordering ? 1 : 0;
  const awaitingStory = stage === "cover_ready" || (stage === "preview_ready" && !Object.values(project.book_profile?.stories || {}).some((text) => String(text || "").trim()));
  const copy = !validPreview ? t.retry : approved ? t.approved : ready ? t.review : creating ? t.creating
    : ordering && flow?.stage === "awaiting_payment_confirmation" ? t.payment : ordering ? t.order
    : storyReview ? t.storyReview : awaitingStory ? t.images : t.preview;

  return (
    <section className="project-journey" aria-label={t.label}>
      <div className="project-journey-overview">
        <div>
          <p className="studio-eyebrow">{approved ? t.done : `${t.step} ${current + 1} ${t.of} 3`}</p>
          <p className="project-journey-lead">{copy[1]}</p>
        </div>
      </div>
      <ol className="project-journey-steps">
        {t.steps.map((label, index) => (
          <li key={label} className={index === current ? "is-current" : index < current ? "is-complete" : ""}
            aria-current={index === current ? "step" : undefined}>
            <span className="project-journey-number" aria-hidden="true">{index < current ? "✓" : `0${index + 1}`}</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
