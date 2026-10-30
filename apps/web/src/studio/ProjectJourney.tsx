import type { Lang } from "../i18n/lang";
import type { Project } from "../types";
import { StudioStepIllustration } from "./StudioStepIllustration";

const COPY = {
  pt: {
    label: "A criação do seu livro", step: "Etapa", of: "de", done: "Livro aprovado",
    steps: ["Prévia e história", "Pedido e criação", "Revisão e entrega"],
    preview: ["Uma história começa a ganhar vida.", "Confira as primeiras imagens e leia a história. Você pode revisar cada detalhe antes de continuar."],
    retry: ["Sua aprovação vem primeiro.", "Vamos preparar uma nova prévia com IA para você revisar. O pedido só continuará após a sua confirmação."],
    order: ["O próximo capítulo é seu livro.", "Confira o formato, os dados de entrega e o resumo do pedido para continuar a criação."],
    payment: ["Acompanhe seu pedido.", "Confira os detalhes abaixo e acompanhe a confirmação do pagamento para iniciar o livro completo."],
    creating: ["Seu livro está ganhando forma.", "As páginas aparecem aqui conforme ficam prontas. Acompanhe os detalhes e prepare-se para a revisão final."],
    review: ["Cada página, do seu jeito.", "Confira o livro completo com calma, peça os ajustes que desejar e confirme a aprovação final."],
    approved: ["Uma história pronta para guardar.", "Seu livro foi aprovado. Acompanhe os próximos passos e os detalhes de entrega no seu pedido."],
  },
  en: {
    label: "Your book's journey", step: "Step", of: "of", done: "Book approved",
    steps: ["Preview and story", "Order and creation", "Review and delivery"],
    preview: ["A story is coming to life.", "Explore the first images and read the story. You can review every detail before continuing."],
    retry: ["Your approval comes first.", "We will prepare a new AI preview for your review. The order will only continue after your confirmation."],
    order: ["The next chapter is your book.", "Review the format, delivery details and order summary to continue creating your book."],
    payment: ["Follow your order.", "Review the details below and track payment confirmation before the complete book is created."],
    creating: ["Your book is taking shape.", "Pages appear here as they become ready. Follow the details and get ready for the final review."],
    review: ["Every page, your way.", "Take your time to review the complete book, request adjustments and give your final approval."],
    approved: ["A story ready to treasure.", "Your book is approved. Follow the next steps and delivery details in your order."],
  },
  es: {
    label: "La creación de tu libro", step: "Paso", of: "de", done: "Libro aprobado",
    steps: ["Vista previa e historia", "Pedido y creación", "Revisión y entrega"],
    preview: ["Una historia empieza a cobrar vida.", "Mira las primeras imágenes y lee la historia. Puedes revisar cada detalle antes de continuar."],
    retry: ["Tu aprobación es lo primero.", "Prepararemos una nueva vista previa con IA para que la revises. El pedido solo continuará después de tu confirmación."],
    order: ["El próximo capítulo es tu libro.", "Revisa el formato, los datos de entrega y el resumen del pedido para continuar la creación."],
    payment: ["Sigue tu pedido.", "Revisa los detalles y sigue la confirmación del pago para comenzar el libro completo."],
    creating: ["Tu libro está tomando forma.", "Las páginas aparecen aquí a medida que están listas. Sigue los detalles y prepárate para la revisión final."],
    review: ["Cada página, a tu manera.", "Revisa el libro completo con calma, solicita los ajustes que quieras y confirma la aprobación final."],
    approved: ["Una historia lista para guardar.", "Tu libro está aprobado. Sigue los próximos pasos y los datos de entrega en tu pedido."],
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
  const copy = !validPreview ? t.retry : approved ? t.approved : ready ? t.review : creating ? t.creating
    : ordering && flow?.stage === "awaiting_payment_confirmation" ? t.payment : ordering ? t.order : t.preview;

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
