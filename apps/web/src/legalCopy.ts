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
  updated: "Última atualização: 23 de outubro de 2026.",
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
      text: "A OpenAI recebe a foto e o texto do projeto só para gerar ilustrações e história. A ElevenLabs recebe a amostra de voz do adulto só quando há narração clonada. O Clerk guarda o login do adulto, sem foto nem idade da criança. Hospedagem, armazenamento, e-mail, pagamento e frete recebem só o necessário para a tarefa. Orientamos esses fornecedores a usar o material apenas para prestar o serviço, sem publicidade e sem treinar modelos próprios.",
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
      text: "A conta é de um adulto. O login exige e-mail verificado. Cada pessoa vê só os próprios projetos. Menores de 13 anos não criam conta e não usam o estúdio.",
    },
    { type: "h", text: "Retenção e exclusão" },
    {
      type: "p",
      text: "A foto, a história e os arquivos do projeto ficam até você apagar o projeto em Meus pedidos, ou até pedir a exclusão da conta. A amostra de voz clonada fica na conta até você apagá-la no estúdio. Não mantemos esses materiais para publicidade. Para corrigir o perfil, use a conta ou o contato desta página.",
    },
    { type: "h", text: "Seus direitos" },
    {
      type: "p",
      text: "Você pode solicitar acesso, correção, portabilidade ou exclusão dos dados, e pode interromper novo uso. No Brasil, esses direitos seguem a LGPD. Apagar um projeto remove a foto e os arquivos daquele livro. A exclusão da conta inteira é pedida pelo contato desta página.",
    },
    { type: "h", text: "Crianças" },
    {
      type: "p",
      text: "O serviço é dirigido a pais e responsáveis com 18 anos ou mais. O envio da foto é feito por essa pessoa, que autoriza o uso apenas para criar o livro. Não coletamos dados de crianças para marketing e não abrimos conta para quem tem menos de 13 anos.",
    },
    { type: "h", text: "Estados Unidos (COPPA)" },
    {
      type: "p",
      text: "Nos Estados Unidos, o COPPA protege dados pessoais de menores de 13 anos, inclusive foto e voz. O Story R Us não é um site para a criança usar. Quem cria a conta confirma ter 18 anos ou mais e ser o pai, a mãe ou o responsável. Nome, idade e foto de quem aparece no livro são informados por esse adulto. Se soubermos que uma conta foi aberta por alguém menor de 13 anos, apagamos a conta e os arquivos. A foto vai para a OpenAI só para ilustrar o livro. A voz, quando existe, é do adulto e vai para a ElevenLabs só para a narração. Não há venda de dados nem publicidade segmentada para crianças. O responsável revisa e apaga cada projeto em Meus pedidos.",
    },
    { type: "h", text: "Alterações" },
    {
      type: "p",
      text: "Podemos atualizar esta política. A data no topo indica a versão vigente. Mudanças relevantes podem ser comunicadas no site ou por e-mail.",
    },
    { type: "h", text: "Contato" },
    { type: "contact", before: "Dúvidas sobre privacidade: " },
  ],
};

const termsPt: LegalDoc = {
  title: "Termos De Uso",
  updated: "Última atualização: 23 de outubro de 2026.",
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
      text: "A conta é pessoal de quem tem 18 anos ou mais. É preciso aceitar estes Termos e a Política de privacidade, declarar a idade e confirmar o e-mail. Crianças menores de 13 anos não podem criar conta nem usar o estúdio. Você é responsável por manter a senha em sigilo e pelas atividades na sua conta.",
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
      text: "Contas e endereços fora do Brasil são aceitos no cadastro. Regras fiscais, impostos de importação ou restrições locais de envio, quando houver impressão internacional, são de responsabilidade do destinatário conforme a legislação aplicável, inclusive o COPPA para usuários nos Estados Unidos.",
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
  updated: "Last updated: October 23, 2026.",
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
      text: "OpenAI receives the photo and project text only to generate illustrations and the story. ElevenLabs receives the adult's voice sample only when a cloned narration is requested. Clerk stores the adult's login, not the child's photo or age. Hosting, storage, email, payment, and shipping receive only what the task needs. We instruct these providers to use the material only to perform the service, with no advertising and no training of their own models.",
    },
    { type: "h", text: "International users" },
    {
      type: "p",
      text: "You can create an account and enter an address outside Brazil. The ebook and digital videos are available regardless of country. Printed books and shipping may be limited to territories our partners serve. The studio says so before any charge.",
    },
    { type: "h", text: "Retention and deletion" },
    {
      type: "p",
      text: "The photo, story, and project files stay until you delete the project in My orders, or until you ask us to delete the account. A cloned voice sample stays on the account until you delete it in the studio. We do not keep these materials for advertising.",
    },
    { type: "h", text: "Your rights" },
    {
      type: "p",
      text: "You can ask to access, correct, or delete personal information, and you can stop further use. Deleting a project removes that book's photo and files. Deleting the whole account is requested through the contact at the end of this page.",
    },
    { type: "h", text: "Children" },
    {
      type: "p",
      text: "The service is directed to parents and guardians who are 18 or older. That adult uploads the photo and authorizes its use only to create this book. We do not collect children's information for marketing, and people under 13 may not create an account or use the studio.",
    },
    { type: "h", text: "United States (COPPA)" },
    {
      type: "p",
      text: "In the United States, COPPA protects personal information from children under 13, including a photograph and a voiceprint. Story R Us is not a site for a child to use. The account holder confirms they are 18 or older and a parent or legal guardian. The child's name, age, and photo are provided by that adult. If we learn an account was opened by someone under 13, we delete the account and its files. The photo goes to OpenAI only to illustrate the book. A voice, when one is provided, is the adult's and goes to ElevenLabs only for narration. We do not sell personal information and we do not serve targeted ads to children. The parent or guardian can review and delete each project from My orders.",
    },
    { type: "h", text: "Changes" },
    {
      type: "p",
      text: "We may update this policy. The date at the top is the current version. Material changes may be posted on the site or sent by email.",
    },
    { type: "h", text: "Contact" },
    { type: "contact", before: "Privacy questions: " },
  ],
};

const termsEn: LegalDoc = {
  title: "Terms Of Use",
  updated: "Last updated: October 23, 2026.",
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
      text: "The account belongs to a person who is 18 or older. You must accept these Terms and the Privacy Policy, confirm your age, and verify your email. Children under 13 may not create an account or use the studio. You are responsible for your password and for activity on your account.",
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
      text: "Accounts and addresses outside Brazil are accepted. Local taxes and import rules, when international printing exists, are the recipient's responsibility under applicable law, including COPPA for people in the United States.",
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
  updated: "Última actualización: 23 de octubre de 2026.",
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
      text: "OpenAI recibe la foto y el texto solo para generar las ilustraciones y la historia. ElevenLabs recibe la muestra de voz del adulto solo si hay narración clonada. Clerk guarda el acceso del adulto, sin la foto ni la edad del niño. Les pedimos usar el material solo para prestar el servicio.",
    },
    { type: "h", text: "Conservación y eliminación" },
    {
      type: "p",
      text: "La foto, la historia y los archivos del proyecto permanecen hasta que eliminas el proyecto en Mis pedidos, o hasta que pides eliminar la cuenta. La muestra de voz permanece hasta que la borras en el estudio.",
    },
    { type: "h", text: "Niños" },
    {
      type: "p",
      text: "El servicio es para padres y responsables de 18 años o más. Esa persona envía la foto y autoriza su uso solo para crear el libro. Quienes tienen menos de 13 años no crean cuenta ni usan el estudio.",
    },
    { type: "h", text: "Estados Unidos (COPPA)" },
    {
      type: "p",
      text: "En Estados Unidos, la COPPA protege los datos personales de menores de 13 años, incluida la foto y la voz. Story R Us no es un sitio para que lo use un niño. Quien crea la cuenta confirma tener 18 años o más y ser el padre, la madre o el tutor. Si sabemos que una cuenta la abrió alguien menor de 13 años, borramos la cuenta y los archivos. No vendemos datos ni mostramos publicidad segmentada a niños. El responsable puede revisar y borrar cada proyecto en Mis pedidos.",
    },
    { type: "h", text: "Contacto" },
    { type: "contact", before: "Preguntas de privacidad: " },
  ],
};

const termsEs: LegalDoc = {
  title: "Términos De Uso",
  updated: "Última actualización: 23 de octubre de 2026.",
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
      text: "La cuenta es de quien tiene 18 años o más. Hay que aceptar estos Términos y la Política de privacidad, declarar la edad y confirmar el correo. Los menores de 13 años no pueden crear cuenta ni usar el estudio.",
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
