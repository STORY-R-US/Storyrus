import type { Lang } from "../i18n/lang";
import type { Project } from "../types";

const COPY = {
  pt: {
    label: "A criação do seu livro", step: "Etapa", of: "de", done: "Livro aprovado",
    steps: ["Prévia e história", "Pedido e criação", "Revisão e entrega"],
    preview: ["Uma história começa a ganhar vida.", "Leia a história com calma. Aprove ou peça ajustes em qualquer página."],
    generating: ["Uma história começa a ganhar vida.", "Estamos criando a capa e as imagens da prévia. Leva alguns minutos e a tela atualiza sozinha."],
    images: ["As imagens da sua prévia", "Confira as imagens. Se gostar, siga para a história completa."],
    retry: ["Sua aprovação vem primeiro.", "Vamos preparar uma nova prévia com IA para você revisar. O pedido só continuará após a sua confirmação."],
    order: ["O próximo capítulo é seu livro.", "Escolha o formato, confira o endereço e finalize o pedido."],
    storyReview: ["História aprovada.", "Confira o resumo e continue para o pedido."],
    payment: ["Acompanhe seu pedido.", "Assim que o pagamento for confirmado, começamos o livro completo."],
    creating: ["Seu livro está ganhando forma.", "As páginas aparecem aqui conforme ficam prontas."],
    review: ["Cada página, do seu jeito.", "Confira o livro completo, peça ajustes se quiser e aprove."],
    approved: ["Uma história pronta para guardar.", "Seu livro foi aprovado e segue para impressão."],
  },
  en: {
    label: "Your Book's Journey", step: "Step", of: "of", done: "Book Approved",
    steps: ["Preview And Story", "Order And Creation", "Review And Delivery"],
    preview: ["A Story Is Coming To Life.", "Read the story at your own pace. Approve it or ask for changes on any page."],
    generating: ["A Story Is Coming To Life.", "We are creating the cover and preview images. It takes a few minutes and this screen updates by itself."],
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
    label: "La creación de tu libro", step: "Paso", of: "de", done: "Libro aprobado",
    steps: ["Vista previa e historia", "Pedido y creación", "Revisión y entrega"],
    preview: ["Una historia empieza a cobrar vida.", "Lee la historia con calma. Apruébala o pide ajustes en cualquier página."],
    generating: ["Una historia empieza a cobrar vida.", "Estamos creando la portada y las imágenes de la vista previa. Tarda unos minutos y la pantalla se actualiza sola."],
    images: ["Las imágenes de tu vista previa", "Revisa las imágenes. Si te gustan, sigue con la historia completa."],
    retry: ["Tu aprobación es lo primero.", "Prepararemos una nueva vista previa con IA para que la revises. El pedido solo continuará después de tu confirmación."],
    order: ["El próximo capítulo es tu libro.", "Elige el formato, revisa la dirección y finaliza el pedido."],
    storyReview: ["Historia aprobada.", "Revisa el resumen y continúa con el pedido."],
    payment: ["Sigue tu pedido.", "Cuando se confirme el pago, empezamos el libro completo."],
    creating: ["Tu libro está tomando forma.", "Las páginas aparecen aquí a medida que están listas."],
    review: ["Cada página, a tu manera.", "Revisa el libro completo, pide ajustes si quieres y apruébalo."],
    approved: ["Una historia lista para guardar.", "Tu libro está aprobado y va a impresión."],
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
    : storyReview ? t.storyReview : awaitingStory ? t.images : stage === "story_ready" ? t.preview : t.generating;

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
