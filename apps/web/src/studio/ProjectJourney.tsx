import type { Lang } from "../i18n/lang";
import type { Project } from "../types";
import { StudioStepIllustration } from "./StudioStepIllustration";

const COPY = {
  pt: {
    label: "A Criação Do Seu Livro", step: "Etapa", of: "de", done: "Livro Aprovado",
    steps: ["Prévia E História", "Pedido E Criação", "Revisão E Entrega"],
    preview: ["Uma História Começa A Ganhar Vida.", "Confira as primeiras imagens e leia a história. Você pode revisar cada detalhe antes de continuar."],
    images: ["As imagens da sua prévia", "Veja a capa, o livro aberto e a leitura. Depois, gere a história."],
    retry: ["Sua Aprovação Vem Primeiro.", "Vamos preparar uma nova prévia com IA para você revisar. O pedido só continuará após a sua confirmação."],
    order: ["O Próximo Capítulo É Seu Livro.", "Confira o formato, os dados de entrega e o resumo do pedido para continuar a criação."],
    payment: ["Acompanhe Seu Pedido.", "Confira os detalhes abaixo e acompanhe a confirmação do pagamento para iniciar o livro completo."],
    creating: ["Seu Livro Está Ganhando Forma.", "As páginas aparecem aqui conforme ficam prontas. Acompanhe os detalhes e prepare-se para a revisão final."],
    review: ["Cada Página, Do Seu Jeito.", "Confira o livro completo com calma, peça os ajustes que desejar e confirme a aprovação final."],
    approved: ["Uma História Pronta Para Guardar.", "Seu livro foi aprovado. Acompanhe os próximos passos e os detalhes de entrega no seu pedido."],
  },
  en: {
    label: "Your Book's Journey", step: "Step", of: "of", done: "Book Approved",
    steps: ["Preview And Story", "Order And Creation", "Review And Delivery"],
    preview: ["A Story Is Coming To Life.", "Explore the first images and read the story. You can review every detail before continuing."],
    images: ["Your preview images", "Look at the cover, the open book, and the reading scene. Then write the story."],
    retry: ["Your Approval Comes First.", "We will prepare a new AI preview for your review. The order will only continue after your confirmation."],
    order: ["The Next Chapter Is Your Book.", "Review the format, delivery details and order summary to continue creating your book."],
    payment: ["Follow Your Order.", "Review the details below and track payment confirmation before the complete book is created."],
    creating: ["Your Book Is Taking Shape.", "Pages appear here as they become ready. Follow the details and get ready for the final review."],
    review: ["Every Page, Your Way.", "Take your time to review the complete book, request adjustments and give your final approval."],
    approved: ["A Story Ready To Treasure.", "Your book is approved. Follow the next steps and delivery details in your order."],
  },
  es: {
    label: "La Creación De Tu Libro", step: "Paso", of: "de", done: "Libro Aprobado",
    steps: ["Vista Previa E Historia", "Pedido Y Creación", "Revisión Y Entrega"],
    preview: ["Una Historia Empieza A Cobrar Vida.", "Mira las primeras imágenes y lee la historia. Puedes revisar cada detalle antes de continuar."],
    images: ["Las imágenes de tu vista previa", "Mira la portada, el libro abierto y la lectura. Después, escribe la historia."],
    retry: ["Tu Aprobación Es Lo Primero.", "Prepararemos una nueva vista previa con IA para que la revises. El pedido solo continuará después de tu confirmación."],
    order: ["El Próximo Capítulo Es Tu Libro.", "Revisa el formato, los datos de entrega y el resumen del pedido para continuar la creación."],
    payment: ["Sigue Tu Pedido.", "Revisa los detalles y sigue la confirmación del pago para comenzar el libro completo."],
    creating: ["Tu Libro Está Tomando Forma.", "Las páginas aparecen aquí a medida que están listas. Sigue los detalles y prepárate para la revisión final."],
    review: ["Cada Página, A Tu Manera.", "Revisa el libro completo con calma, solicita los ajustes que quieras y confirma la aprobación final."],
    approved: ["Una Historia Lista Para Guardar.", "Tu libro está aprobado. Sigue los próximos pasos y los datos de entrega en tu pedido."],
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
  const current = approved || ready ? 2 : creating || ordering ? 1 : 0;
  const awaitingStory = stage === "preview_ready" && !Object.values(project.book_profile?.stories || {}).some((text) => String(text || "").trim());
  const copy = !validPreview ? t.retry : approved ? t.approved : ready ? t.review : creating ? t.creating
    : ordering && flow?.stage === "awaiting_payment_confirmation" ? t.payment : ordering ? t.order
    : awaitingStory ? t.images : t.preview;

  return (
    <section className="project-journey" aria-label={t.label}>
      <div className="project-journey-overview">
        <div>
          <p className="studio-eyebrow">{approved ? t.done : `${t.step} ${current + 1} ${t.of} 3`}</p>
          <h3>{copy[0]}</h3>
          <p className="project-journey-lead">{copy[1]}</p>
        </div>
        <StudioStepIllustration step={current === 2 ? 2 : current === 1 && !creating ? 3 : 1} />
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
