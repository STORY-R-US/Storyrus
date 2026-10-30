import type { Lang } from "./i18n/lang";

export const LEGAL_CONTACT = "info@storyrus.ai";

export type LegalBlock =
  | { type: "p"; text: string }
  | { type: "h"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "link"; before: string; href: string; label: string; after: string }
  | { type: "contact"; before: string };

export type LegalDoc = {
  title: string;
  updated: string;
  home: string;
  back: string;
  blocks: LegalBlock[];
};

const privacyPt: LegalDoc = {
  title: "Política De Privacidade",
  updated: "Última atualização: 29 de outubro de 2026.",
  home: "Início",
  back: "Voltar à página inicial",
  blocks: [
    {
      type: "p",
      text: "A Story R Us (storyrus.ai) cria livros ilustrados personalizados a partir de uma foto que um adulto envia. Esta política explica quais dados tratamos, para quê e como você pode exercer seus direitos — no Brasil (LGPD) e nos Estados Unidos (COPPA).",
    },
    { type: "h", text: "Quem somos" },
    {
      type: "p",
      text: "Controladora dos dados: Story R Us. O contato de privacidade está no final desta página.",
    },
    { type: "h", text: "O que coletamos" },
    {
      type: "ul",
      items: [
        "Conta do adulto: e-mail e senha ficam no Clerk. Guardamos nome, telefone, endereço, data de cadastro, aceite dos termos e a declaração de que a pessoa tem 18 anos ou mais.",
        "Projeto: nome, idade e dedicatória de quem aparece no livro, foto enviada, estilo, tema e o conteúdo gerado (personagem, páginas, PDF e vídeo).",
        "Voz: se o adulto enviar um áudio, a amostra é dele, para narrar o livro. Não pedimos voz de criança.",
        "Uso técnico: sessão no navegador e registros necessários à segurança. Quando houver pagamento ou frete, os dados do pedido.",
      ],
    },
    { type: "h", text: "Para que usamos" },
    {
      type: "p",
      text: "Criar e entregar o livro e os vídeos do projeto, autenticar a conta, enviar e-mails transacionais e processar a impressão quando você pedir. Não vendemos dados pessoais, não fazemos publicidade segmentada e não usamos a foto nem a voz para divulgação, marketing ou treino de modelos.",
    },
    { type: "h", text: "Base e finalidade" },
    {
      type: "p",
      text: "Tratamos os dados para executar o contrato (criar o livro) e, no que depender de autorização, com o consentimento de quem tem 18 anos ou mais e declara ser o responsável legal ao enviar a foto.",
    },
    { type: "h", text: "Compartilhamento com fornecedores" },
    {
      type: "p",
      text: "Fotos, características e texto podem ser enviados à OpenAI para gerar o livro; áudio de adulto à ElevenLabs para narração; conteúdo necessário à Kling para vídeo, quando esse recurso for solicitado. Clerk cuida do login. Hospedagem, armazenamento, e-mail, pagamento e impressão recebem os dados necessários à sua função. Esses dados não são destinados a anúncios ou venda. Condições de retenção e uso dos fornecedores precisam ser compatíveis com a finalidade contratada.",
    },
    { type: "h", text: "Usuários internacionais" },
    {
      type: "p",
      text: "Você pode criar conta e informar endereço fora do Brasil. O ebook e os vídeos digitais estão disponíveis independentemente do país. A impressão física e o frete podem estar limitados aos territórios atendidos pelos parceiros; o estúdio avisa antes da cobrança.",
    },
    { type: "h", text: "Exemplos Da Página Inicial" },
    {
      type: "link",
      before: "As fotos de demonstração no site são materiais da plataforma, separados do que você envia no estúdio. A página ",
      href: "/exemplos",
      label: "exemplos",
      after: " explica isso e aponta a vitrine da página inicial.",
    },
    { type: "h", text: "Conta e sessão" },
    {
      type: "p",
      text: "Serviço exclusivo para adultos responsáveis com 18 anos ou mais. Crianças e adolescentes não criam conta nem utilizam o Estúdio.",
    },
    { type: "h", text: "Retenção e exclusão" },
    {
      type: "p",
      text: "Guardamos os dados do projeto apenas enquanto necessários à criação, entrega e atendimento do pedido. Projetos sem pagamento são apagados após 90 dias sem abertura ou outra atividade registrada. Pagamentos pendentes, pedidos pagos e gerações em andamento ficam fora dessa limpeza automática. O adulto pode excluir o projeto em Meus pedidos e solicitar o encerramento da conta. A exclusão inclui fotos, arquivos gerados, cópias de prévia e amostras de voz sob nosso controle. Registros comerciais cuja guarda seja necessária são tratados separadamente dos materiais infantis. Cópias de segurança e dados já recebidos por fornecedores seguem seus próprios ciclos de eliminação; solicite informações pelo contato de privacidade.",
    },
    { type: "h", text: "Seus direitos" },
    {
      type: "p",
      text: "Você pode solicitar acesso, correção, portabilidade ou exclusão dos dados, e pode interromper novo uso. No Brasil, esses direitos seguem a LGPD. Apagar um projeto remove a foto e os arquivos daquele livro. A exclusão da conta inteira é pedida pelo contato desta página.",
    },
    { type: "h", text: "Crianças" },
    {
      type: "p",
      text: "Serviço exclusivo para adultos responsáveis com 18 anos ou mais. Crianças e adolescentes não criam conta nem utilizam o Estúdio.",
    },
    { type: "h", text: "Estados Unidos (COPPA)" },
    {
      type: "p",
      text: "A COPPA trata da coleta online de dados de menores de 13 anos. O serviço Story R Us é exclusivo para adultos responsáveis de 18 anos ou mais: a criança não cria conta, envia arquivos nem opera o Estúdio. Os dados de quem aparece no livro são fornecidos pelo adulto. A autorização registrada no envio não é apresentada como consentimento parental verificável para um serviço usado por crianças. Se identificarmos uso por menor de idade, restringimos a conta e tratamos a exclusão pelo contato de privacidade.",
    },
    { type: "h", text: "Alterações" },
    {
      type: "p",
      text: "Podemos atualizar esta política. A data no topo indica a versão vigente. Mudanças relevantes podem ser comunicadas no site ou por e-mail.",
    },
    {"type":"h","text":"Autorização e controle do responsável"},
    {"type":"p","text":"Antes de enviar arquivos, o adulto deve ler o aviso e autorizar o tratamento. Registramos a versão do aviso, o momento, a conta e a finalidade da autorização. Ela cobre a execução do pedido, sem autorização para publicar o material ou fazer publicidade. Você pode pedir a interrupção de novos usos, revisar os projetos e solicitar exclusão em info@storyrus.ai. Não envie dados de uma criança sem autoridade para isso."},
    {"type":"h","text":"Processamento de imagens e informações sensíveis"},
    {"type":"p","text":"As fotos podem passar por processamento automatizado e comparação de semelhança para manter a aparência nas ilustrações. Essa comparação não verifica a identidade ou a idade do adulto. Não pedimos documento da criança, localização exata, escola ou informações de saúde para criar um livro. Use apenas o primeiro nome ou apelido e a idade necessária à história. A localização aproximada por IP pode ser consultada para sugerir o idioma; você pode escolher o idioma manualmente."},
    { type: "h", text: "Contato" },
    { type: "contact", before: "Dúvidas sobre privacidade: " },
  ],
};

const termsPt: LegalDoc = {
  title: "Termos De Uso",
  updated: "Última atualização: 29 de outubro de 2026.",
  home: "Início",
  back: "Voltar à página inicial",
  blocks: [
    {
      type: "p",
      text: "Ao criar conta ou usar storyrus.ai você concorda com estes Termos de uso. Se não concordar, não utilize o serviço.",
    },
    { type: "h", text: "O serviço" },
    {
      type: "p",
      text: "A Story R Us gera histórias e ilustrações com inteligência artificial a partir dos dados e da foto que o adulto envia. O resultado pode variar. Você revisa a prévia antes de baixar o PDF ou pedir o livro impresso.",
    },
    { type: "h", text: "Cadastro e conta" },
    {
      type: "p",
      text: "Serviço exclusivo para adultos responsáveis com 18 anos ou mais. Crianças e adolescentes não criam conta nem utilizam o Estúdio. O acesso exige e-mail verificado e aceite dos Termos e da Política de privacidade.",
    },
    { type: "h", text: "Responsável legal" },
    {
      type: "p",
      text: "Só envie foto de criança se você for o responsável legal e autorizar o uso exclusivo para criar este livro. A voz clonada, quando houver, é a sua, de adulto, e não a da criança. Foto e voz não são usadas para divulgação, publicidade ou treino de modelos.",
    },
    { type: "h", text: "Pagamento do livro impresso" },
    {
      type: "p",
      text: "Gerar a história e as imagens entra no pedido. O que se fatura é o livro impresso, na ordem de serviço, conforme tamanho, acabamento, quantidade e frete. O parcelamento no cartão depende do gateway de pagamento estar ativo; até lá, o pedido de impresso pode seguir como cotação.",
    },
    { type: "h", text: "Impressão e envio" },
    {
      type: "p",
      text: "Quando a impressão estiver disponível, o endereço de entrega deve estar completo e válido. Entregas físicas podem estar restritas às regiões atendidas pelos parceiros logísticos. Fora dessas áreas, o livro digital (PDF) continua disponível no pedido.",
    },
    { type: "h", text: "Usuários internacionais" },
    {
      type: "p",
      text: "Contas e endereços fora do Brasil são aceitos. A disponibilidade de impressão e entrega depende dos parceiros e é informada antes da cobrança. O tratamento de dados continua sujeito à nossa Política de privacidade.",
    },
    { type: "h", text: "Propriedade e uso" },
    {
      type: "p",
      text: "Você pode usar o livro gerado para uso pessoal e familiar. Não redistribua o software, não explore falhas da API e não use o serviço para conteúdo ilegal, abusivo ou que viole direitos de terceiros.",
    },
    { type: "h", text: "Limitação" },
    {
      type: "p",
      text: "O serviço é oferecido “como está”. Na medida permitida pela lei, não garantimos disponibilidade ininterrupta nem resultado artístico específico. Em caso de falha imputável a nós, a responsabilidade limita-se, em regra, a refazer o livro ou o pedido afetado.",
    },
    { type: "h", text: "Alterações e vigência" },
    {
      type: "p",
      text: "Podemos atualizar estes termos. A data no topo indica a versão vigente. O uso continuado após a publicação das alterações constitui aceite, salvo quando a lei exigir novo consentimento.",
    },
    { type: "h", text: "Contato" },
    { type: "contact", before: "Contato: " },
  ],
};

const privacyEn: LegalDoc = {
  title: "Privacy Policy",
  updated: "Last updated: October 29, 2026.",
  home: "Home",
  back: "Back to home",
  blocks: [
    {
      type: "p",
      text: "Story R Us (storyrus.ai) creates personalized illustrated books from a photo sent by an adult. This policy explains what we process, why, and how you can use your rights, including under the US Children's Online Privacy Protection Act (COPPA).",
    },
    { type: "h", text: "Who we are" },
    {
      type: "p",
      text: "Data controller: Story R Us. The privacy contact is at the end of this page.",
    },
    { type: "h", text: "What we collect" },
    {
      type: "ul",
      items: [
        "Adult account: email and password stay with Clerk. We store name, phone, address, signup date, acceptance of these terms, and the statement that the person is 18 or older.",
        "Project: name, age, and dedication of the person in the book, the photo you upload, style, theme, and the generated book (character, pages, PDF, and video).",
        "Voice: if an adult uploads audio, the sample is theirs and is used to narrate the book. We do not ask for a child's voice.",
        "Technical use: a session in the browser and security logs. Order data when payment or shipping is active.",
      ],
    },
    { type: "h", text: "How we use it" },
    {
      type: "p",
      text: "We use the data to create and deliver the book and videos, sign you in, send transactional email, and print the book when you ask. We do not sell personal information, we do not run targeted advertising, and we do not use the photo or voice for promotion or model training.",
    },
    { type: "h", text: "Processors" },
    {
      type: "p",
      text: "Photos, character details and text may go to OpenAI for book generation; adult audio to ElevenLabs for narration; necessary content to Kling for video when requested. Clerk handles sign-in. Hosting, storage, email, payment and printing providers receive information necessary for their role. This information is not intended for advertising or sale. Providers' retention and use conditions must be compatible with the contracted purpose.",
    },
    { type: "h", text: "International users" },
    {
      type: "p",
      text: "You can create an account and enter an address outside Brazil. The ebook and digital videos are available regardless of country. Printed books and shipping may be limited to territories our partners serve. The studio says so before any charge.",
    },
    { type: "h", text: "Retention and deletion" },
    {
      type: "p",
      text: "We keep project information only as necessary to create, deliver and support the order. Unpaid projects are deleted after 90 days without opening or other recorded activity. Pending payments, paid orders and active generation are excluded from this automated cleanup. Adults can delete projects in My orders and request account closure. Deletion includes photos, generated files, preview copies and voice samples under our control. Necessary commercial records are handled separately from children's materials. Backups and information already received by providers follow their own deletion cycles; contact us for details.",
    },
    { type: "h", text: "Your rights" },
    {
      type: "p",
      text: "You can ask to access, correct, or delete personal information, and you can stop further use. Deleting a project removes that book's photo and files. Deleting the whole account is requested through the contact at the end of this page.",
    },
    { type: "h", text: "Children" },
    {
      type: "p",
      text: "For adult parents and guardians aged 18 and over only. Children and teenagers cannot create accounts or use the Studio.",
    },
    { type: "h", text: "United States (COPPA)" },
    {
      type: "p",
      text: "COPPA addresses online collection of information from children under 13. Story R Us is exclusively for adult parents and guardians aged 18 and over: children do not create accounts, upload files or operate the Studio. Information about book characters is provided by the adult. The recorded upload authorization is not represented as verifiable parental consent for a child-operated service. If we identify use by a minor, we restrict the account and handle deletion through our privacy contact.",
    },
    { type: "h", text: "Changes" },
    {
      type: "p",
      text: "We may update this policy. The date at the top is the current version. Material changes may be posted on the site or sent by email.",
    },
    {"type":"h","text":"Adult authorization and control"},
    {"type":"p","text":"Before uploading, the adult must read the notice and authorize processing. We record the notice version, time, account and purpose. This covers fulfilling the order, not publishing materials or advertising. Request an end to further uses, review projects or request deletion at info@storyrus.ai. Do not submit a child's information without authority to do so."},
    {"type":"h","text":"Image processing and sensitive information"},
    {"type":"p","text":"Photos may undergo automated processing and similarity comparison to maintain appearance in illustrations. This does not verify the adult's identity or age. A child's identity documents, precise location, school and health information are not needed for a book. Use a first name or nickname and the age needed for the story. An approximate IP location may be consulted to suggest a language; you can choose a language manually."},
    { type: "h", text: "Contact" },
    { type: "contact", before: "Privacy questions: " },
  ],
};

const termsEn: LegalDoc = {
  title: "Terms Of Use",
  updated: "Last updated: October 29, 2026.",
  home: "Home",
  back: "Back to home",
  blocks: [
    {
      type: "p",
      text: "By creating an account or using storyrus.ai you agree to these Terms of Use. If you do not agree, do not use the service.",
    },
    { type: "h", text: "The service" },
    {
      type: "p",
      text: "Story R Us generates stories and illustrations with artificial intelligence from the information and photo an adult sends. Results vary. You review the preview before downloading the PDF or ordering a printed book.",
    },
    { type: "h", text: "Account" },
    {
      type: "p",
      text: "For adult parents and guardians aged 18 and over only. Children and teenagers cannot create accounts or use the Studio. Access requires verified email and acceptance of the Terms and Privacy Policy.",
    },
    { type: "h", text: "Legal guardian" },
    {
      type: "p",
      text: "Upload a child's photo only if you are the legal guardian and you authorize its use solely to create this book. A cloned voice, if you provide one, is your adult voice, not the child's. Photos and voice are not used for promotion, advertising, or model training.",
    },
    { type: "h", text: "Printed book payment" },
    {
      type: "p",
      text: "The story and images are part of the order. What is billed is the printed book, according to size, binding, quantity, and shipping. Card installments depend on the payment gateway. Until then, a print request may remain a quotation.",
    },
    { type: "h", text: "Printing and shipping" },
    {
      type: "p",
      text: "When printing is available, the delivery address must be complete and valid. Physical delivery may be limited to regions our logistics partners serve. Elsewhere, the digital book (PDF) remains available on the order.",
    },
    { type: "h", text: "International users" },
    {
      type: "p",
      text: "Accounts and addresses outside Brazil are accepted. Print and delivery availability depends on our partners and is shown before payment. Information handling remains subject to our Privacy Policy.",
    },
    { type: "h", text: "Ownership and use" },
    {
      type: "p",
      text: "You may use the generated book for personal and family use. Do not redistribute the software, probe the API, or use the service for illegal or abusive content or to infringe someone else's rights.",
    },
    { type: "h", text: "Contact" },
    { type: "contact", before: "Contact: " },
  ],
};

const privacyEs: LegalDoc = {
  title: "Política De Privacidad",
  updated: "Última actualización: 29 de octubre de 2026.",
  home: "Inicio",
  back: "Volver al inicio",
  blocks: [
    {
      type: "p",
      text: "Story R Us (storyrus.ai) crea libros ilustrados personalizados a partir de una foto que envía un adulto. Esta política explica qué datos tratamos y cómo ejercer tus derechos, incluso bajo la COPPA de Estados Unidos.",
    },
    { type: "h", text: "Quiénes somos" },
    {
      type: "p",
      text: "Responsable: Story R Us. El contacto de privacidad está al final de esta página.",
    },
    { type: "h", text: "Qué recopilamos" },
    {
      type: "ul",
      items: [
        "Cuenta del adulto: el correo y la contraseña quedan en Clerk. Guardamos nombre, teléfono, dirección, la aceptación de los términos y la declaración de tener 18 años o más.",
        "Proyecto: nombre, edad y dedicatoria de quien aparece en el libro, la foto, el estilo, el tema y el contenido generado.",
        "Voz: si el adulto envía un audio, la muestra es suya, para narrar el libro. No pedimos la voz de un niño.",
      ],
    },
    { type: "h", text: "Para qué los usamos" },
    {
      type: "p",
      text: "Crear y entregar el libro y los videos, autenticar la cuenta y, si lo pides, imprimir. No vendemos datos, no hacemos publicidad segmentada y no usamos la foto ni la voz para difusión ni para entrenar modelos.",
    },
    { type: "h", text: "Proveedores" },
    {
      type: "p",
      text: "Las fotos, características y textos pueden enviarse a OpenAI para crear el libro; el audio de adulto a ElevenLabs para narración; y el contenido necesario a Kling para vídeos solicitados. Clerk gestiona el acceso. Alojamiento, almacenamiento, correo, pagos e impresión reciben lo necesario para su función. No destinamos estos datos a publicidad ni venta. Las condiciones de retención y uso de los proveedores deben ser compatibles con la finalidad contratada.",
    },
    { type: "h", text: "Conservación y eliminación" },
    {
      type: "p",
      text: "Guardamos los datos solo mientras sean necesarios para crear, entregar y atender el pedido. Los proyectos sin pago se eliminan tras 90 días sin abrirse ni otra actividad registrada. Los pagos pendientes, pedidos pagados y generaciones activas quedan fuera de esta limpieza automática. El adulto puede borrar proyectos en Mis pedidos y solicitar el cierre de la cuenta. Esto incluye fotos, archivos generados, copias de vista previa y muestras de voz bajo nuestro control. Los registros comerciales necesarios se gestionan por separado. Las copias de seguridad y los proveedores tienen sus propios ciclos de eliminación; contacta con nosotros para más información.",
    },
    { type: "h", text: "Niños" },
    {
      type: "p",
      text: "Servicio exclusivo para padres y responsables mayores de 18 años. Los menores no pueden crear cuentas ni utilizar el Estudio.",
    },
    { type: "h", text: "Estados Unidos (COPPA)" },
    {
      type: "p",
      text: "La COPPA regula la recopilación en línea de datos de menores de 13 años. Story R Us es exclusivo para padres y responsables mayores de 18 años: los menores no crean cuentas, envían archivos ni usan el Estudio. El adulto facilita los datos de quienes aparecen en el libro. La autorización registrada no se presenta como consentimiento parental verificable para un servicio usado por menores. Si identificamos ese uso, restringimos la cuenta y gestionamos su eliminación mediante el contacto de privacidad.",
    },
    {"type":"h","text":"Autorización y control del responsable"},
    {"type":"p","text":"Antes de enviar archivos, el adulto debe leer el aviso y autorizar el tratamiento. Registramos versión, momento, cuenta y finalidad. La autorización cubre el pedido, no la publicación del material ni publicidad. Puedes pedir el cese de nuevos usos, revisar proyectos o solicitar su eliminación en info@storyrus.ai. No envíes datos de un menor sin autoridad para hacerlo."},
    {"type":"h","text":"Tratamiento de imágenes e información sensible"},
    {"type":"p","text":"Las fotos pueden procesarse automáticamente y compararse para conservar la apariencia en las ilustraciones. Esto no verifica la identidad ni la edad del adulto. No necesitamos documentos, ubicación exacta, escuela o datos de salud del menor. Usa el nombre o apodo y la edad necesaria para la historia. Podemos consultar una ubicación aproximada por IP para sugerir idioma; puedes cambiarlo manualmente."},
    { type: "h", text: "Contacto" },
    { type: "contact", before: "Preguntas de privacidad: " },
  ],
};

const termsEs: LegalDoc = {
  title: "Términos De Uso",
  updated: "Última actualización: 29 de octubre de 2026.",
  home: "Inicio",
  back: "Volver al inicio",
  blocks: [
    {
      type: "p",
      text: "Al crear una cuenta o usar storyrus.ai aceptas estos Términos de uso. Si no estás de acuerdo, no uses el servicio.",
    },
    { type: "h", text: "El servicio" },
    {
      type: "p",
      text: "Story R Us genera historias e ilustraciones con inteligencia artificial a partir de los datos y de la foto que envía un adulto. Tú revisas la vista previa antes de descargar el PDF o pedir el libro impreso.",
    },
    { type: "h", text: "Cuenta" },
    {
      type: "p",
      text: "Servicio exclusivo para padres y responsables mayores de 18 años. Los menores no pueden crear cuentas ni utilizar el Estudio. El acceso requiere correo verificado y aceptación de los Términos y la Política de privacidad.",
    },
    { type: "h", text: "Responsable legal" },
    {
      type: "p",
      text: "Envía la foto de un niño solo si eres el responsable legal y autorizas el uso exclusivo para crear este libro. La voz clonada, si la hay, es la tuya, de adulto, y no la del niño.",
    },
    { type: "h", text: "Contacto" },
    { type: "contact", before: "Contacto: " },
  ],
};

const DOCS: Record<Lang, { privacy: LegalDoc; terms: LegalDoc }> = {
  pt: { privacy: privacyPt, terms: termsPt },
  en: { privacy: privacyEn, terms: termsEn },
  es: { privacy: privacyEs, terms: termsEs },
};

export function legalLang(pathname: string, site: Lang): Lang {
  if (pathname === "/privacy" || pathname === "/terms") return "en";
  if (site === "en" || site === "es") return site;
  return "pt";
}

export function legalDocument(lang: Lang, kind: "privacy" | "terms"): LegalDoc {
  return DOCS[lang][kind];
}
