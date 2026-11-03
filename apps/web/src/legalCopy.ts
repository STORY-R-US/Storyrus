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
  updated: "Última atualização: 2 de novembro de 2026.",
  home: "Início",
  back: "Voltar à página inicial",
  blocks: [
    {
      type: "p",
      text: "A Story R Us (storyrus.ai) cria livros ilustrados personalizados com os dados e as fotos enviados por um adulto responsável. Esta política explica quais dados tratamos, para quê e como exercer seus direitos. A LGPD brasileira e outras regras de proteção de dados se aplicam conforme o caso; a seção sobre crianças explica o modelo do serviço e as considerações sobre a COPPA dos Estados Unidos.",
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
        "Conta do adulto: a autenticação atual é feita pelo Clerk. Mantemos e-mail, identificador da conta, nome, telefone, endereço informado, data de cadastro e registros de aceite e de declaração de maioridade.",
        "Projeto: nome ou apelido, idade, dedicatória, fotos dos personagens, tema, estilo, orientações, aprovações e arquivos gerados, como ilustrações, páginas e PDF.",
        "Pedido: formato, acabamento, quantidade, dados do destinatário e da entrega, cotação, estado do pagamento e histórico de atendimento, quando aplicáveis.",
        "Uso técnico: dados de sessão, preferências de idioma e aparência, IP e registros necessários à operação e à segurança. Recursos opcionais de áudio e vídeo, quando disponíveis e solicitados, são tratados separadamente abaixo.",
      ],
    },
    { type: "h", text: "Para que usamos" },
    {
      type: "p",
      text: "Usamos os dados necessários para criar e entregar o livro, manter a conta, enviar comunicações sobre o serviço, atender solicitações e preparar a impressão e a entrega quando pedidas. A autorização do Estúdio cobre o livro; ela não autoriza automaticamente voz, vídeo, publicação ou publicidade. Não vendemos dados pessoais, não fazemos publicidade segmentada e não usamos os arquivos enviados para nossa própria divulgação ou treinamento de modelos.",
    },
    { type: "h", text: "Base e finalidade" },
    {
      type: "p",
      text: "Os dados da conta e do pedido são tratados para prestar o serviço e executar o contrato. Quando necessário, conservamos informações para cumprir obrigações legais ou exercer direitos. O uso das fotos no livro depende da autorização específica apresentada ao adulto antes do envio. Quando o tratamento se basear em consentimento, ele pode ser revogado. Dados de crianças e adolescentes exigem atenção ao seu melhor interesse; a declaração de maioridade de quem envia não dispensa essa proteção.",
    },
    { type: "h", text: "Compartilhamento com fornecedores" },
    {
      type: "p",
      text: "Quando a geração por IA estiver disponível e for solicitada, fotos, características e textos necessários podem ser processados pela OpenAI. O login utiliza o Clerk; o site e a API usam Vercel e Render, e os arquivos podem ser armazenados em serviços compatíveis com S3, incluindo Cloudflare R2. Fornecedores de e-mail, pagamento, gráfica e entrega recebem apenas os dados necessários à etapa solicitada. O modo de teste genérico informado no Estúdio não faz chamadas aos provedores de IA para gerar seu conteúdo. Retenção e demais condições de cada fornecedor dependem do serviço contratado; solicite os detalhes pelo contato de privacidade.",
    },
    { type: "h", text: "Voz E Vídeo Opcionais" },
    { type: "p", text: "A criação do livro não exige o envio de voz nem um pedido de vídeo. Caso esses recursos estejam disponíveis, a amostra de voz deve ser do próprio adulto e exige autorização específica no envio; o áudio pode ser processado pela ElevenLabs. Conteúdo necessário a um vídeo solicitado pode ser processado pela Kling. A autorização das fotos para o livro não substitui a informação e a autorização exigidas para uma finalidade adicional. Arquivos antigos desses recursos e vozes salvas na conta continuam sujeitos a esta política." },
    { type: "h", text: "Transferências Internacionais De Dados" },
    { type: "p", text: "Os fornecedores podem processar dados fora do Brasil. As exigências da LGPD sobre transferências internacionais se aplicam quando cabíveis. Você pode solicitar informações sobre os países de processamento, destinatários e salvaguardas da operação pelo contato de privacidade. Criar uma conta ou aceitar esta política não equivale a uma autorização genérica para qualquer transferência ou nova finalidade." },
    { type: "h", text: "Usuários internacionais" },
    {
      type: "p",
      text: "É possível informar endereço fora do Brasil. A disponibilidade do serviço digital, da impressão e da entrega depende dos recursos e parceiros disponíveis. As condições do pedido devem ser conferidas antes da confirmação e de eventual cobrança.",
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
      text: "Os projetos sem pagamento entram na rotina de exclusão após 90 dias sem abertura ou outra atividade registrada. Pagamentos pendentes, pedidos pagos e gerações em andamento não entram nessa rotina; a conservação deve se limitar ao necessário ao pedido, atendimento, obrigações legais ou exercício de direitos. Em Meus pedidos, o adulto pode excluir o projeto e seus arquivos; tarefas em andamento precisam terminar ou ser interrompidas antes da exclusão. Apagar um projeto não apaga a conta no Clerk nem uma voz reutilizável salva na conta. A exclusão dessas vozes e o encerramento da conta podem ser solicitados pelo contato de privacidade. Cópias de segurança, versões anteriores de arquivos e dados já recebidos por fornecedores podem exigir etapas e prazos adicionais. Informaremos o alcance, os prazos aplicáveis e eventual necessidade de conservação ao atender a solicitação.",
    },
    { type: "h", text: "Seus direitos" },
    {
      type: "p",
      text: "Conforme a legislação aplicável, você pode pedir confirmação do tratamento, acesso e correção dos dados; informação sobre compartilhamentos; anonimização, bloqueio ou eliminação de dados desnecessários ou tratados irregularmente; portabilidade nos termos da regulamentação; revogação do consentimento e eliminação dos dados tratados com base nele, ressalvadas as hipóteses legais de conservação. Você também pode pedir informações sobre a possibilidade de não consentir e suas consequências e apresentar reclamação à ANPD. As solicitações são gratuitas e podem ser enviadas a info@storyrus.ai. Podemos pedir apenas as informações necessárias para confirmar sua identidade e sua autoridade para agir pelo titular. Os prazos e eventuais limites legais serão informados na resposta. A revogação impede novos usos abrangidos por ela, mas não desfaz automaticamente tratamentos anteriores ou o pedido já executado.",
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
      text: "Podemos atualizar esta política. A data no topo identifica a versão do texto. Mudanças relevantes podem ser comunicadas no site ou por e-mail. Uma nova finalidade que exija consentimento precisa ser informada e autorizada separadamente.",
    },
    {"type":"h","text":"Autorização e controle do responsável"},
    {"type":"p","text":"Antes de enviar fotos, o adulto deve ler o aviso e confirmar a autorização para criar o livro. Registramos a versão do aviso, o momento, a conta e a finalidade. Em Meus pedidos, é possível retirar a autorização de novos usos das fotos; essa ação é diferente de apagar o projeto. A autorização não permite publicar os arquivos nem usá-los em publicidade. Não envie dados de uma criança sem ser responsável legal ou estar autorizado por ele. Solicitações adicionais podem ser feitas a info@storyrus.ai."},
    {"type":"h","text":"Processamento de imagens e informações sensíveis"},
    {"type":"p","text":"As fotos podem passar por processamento automatizado e comparação de semelhança para manter a aparência nas ilustrações. Essa comparação não verifica a identidade ou a idade do adulto. Não pedimos documento da criança, localização exata, escola ou informações de saúde para criar um livro. Use apenas o primeiro nome ou apelido e a idade necessária à história."},
    { type: "h", text: "Sessão, Preferências E Serviços Do Navegador" },
    { type: "p", text: "O navegador pode guardar informações de sessão e preferências de idioma e aparência em cookies ou armazenamento local. Sem uma preferência de idioma salva, há uma consulta ao serviço ipapi.co para sugerir o idioma com base no país do IP; o serviço recebe os dados técnicos dessa conexão. Você pode mudar o idioma manualmente. As fontes do site são carregadas do Google Fonts, que também recebe os dados técnicos necessários à conexão. Apagar os dados do navegador pode encerrar a sessão ou remover preferências, mas não exclui os projetos guardados na conta." },
    { type: "h", text: "Acesso E Segurança" },
    { type: "p", text: "O acesso aos projetos depende da conta e das permissões do serviço; a equipe autorizada pode acessá-los para operação e atendimento. Os arquivos são disponibilizados por links de acesso temporário quando esse mecanismo de armazenamento é utilizado. Não publique nem compartilhe links privados. Nenhum sistema oferece segurança absoluta; informe suspeitas de acesso indevido pelo contato desta política." },
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
  updated: "Last updated: November 2, 2026.",
  home: "Home",
  back: "Back to home",
  blocks: [
    {
      type: "p",
      text: "Story R Us (storyrus.ai) creates personalized illustrated books using information and photos provided by a responsible adult. This policy explains what we process, why, and how to exercise your rights. Brazil's LGPD and other privacy rules apply where relevant; the children's section explains the service model and considerations under the US Children's Online Privacy Protection Act (COPPA).",
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
        "Adult account: current authentication is provided by Clerk. We keep email, account identifier, name, phone, address provided, signup date and records of acceptance and the declaration of adult status.",
        "Project: name or nickname, age, dedication, character photos, theme, style, instructions, approvals and generated files such as illustrations, pages and PDF.",
        "Order: format, finish, quantity, recipient and delivery details, quotation, payment status and support history, where applicable.",
        "Technical use: session information, language and appearance preferences, IP and records needed for operation and security. Optional audio and video resources, when available and requested, are addressed separately below.",
      ],
    },
    { type: "h", text: "How we use it" },
    {
      type: "p",
      text: "We use necessary information to create and deliver the book, maintain your account, send service communications, provide support and arrange printing and delivery when requested. The Studio authorization covers the book; it does not automatically authorize voice, video, publication or advertising. We do not sell personal information, run targeted advertising or use uploaded files for our own promotion or model training.",
    },
    { type: "h", text: "Purposes And Legal Grounds" },
    { type: "p", text: "Account and order information is processed to provide the service and perform the contract. Information may also be kept to meet legal obligations or exercise rights. Using photos in a book requires the specific authorization shown to the adult before upload. Consent-based processing can be withdrawn. Children's information requires attention to their best interests; an adult's declaration of age does not remove that protection. Brazilian LGPD rights and legal requirements apply where relevant." },
    { type: "h", text: "Processors" },
    {
      type: "p",
      text: "When AI generation is available and requested, necessary photos, character details and text may be processed by OpenAI. Clerk handles sign-in; the site and API use Vercel and Render, and files may be stored in S3-compatible services including Cloudflare R2. Email, payment, printing and delivery providers receive information needed for the requested step. The generic test mode identified in the Studio does not call AI providers to generate its content. Provider retention and other conditions depend on the contracted service; contact us for details.",
    },
    { type: "h", text: "Optional Voice And Video" },
    { type: "p", text: "Creating a book does not require a voice upload or a video request. If these resources are available, a voice sample must be the adult's own voice and requires specific authorization on upload; audio may be processed by ElevenLabs. Content needed for a requested video may be processed by Kling. Book-photo authorization does not replace the notice and authorization required for an additional purpose. Existing files from these resources and voices saved to an account remain subject to this policy." },
    { type: "h", text: "International Data Transfers" },
    { type: "p", text: "Providers may process information outside Brazil. LGPD requirements on international transfers apply where relevant. Contact us for information about processing countries, recipients and safeguards for the operation. Creating an account or accepting this policy is not blanket authorization for any transfer or new purpose." },
    { type: "h", text: "International users" },
    {
      type: "p",
      text: "You may enter an address outside Brazil. Digital service, printing and delivery availability depend on available resources and partners. Review order conditions before confirming an order and any charge.",
    },
    { type: "h", text: "Retention and deletion" },
    {
      type: "p",
      text: "Unpaid projects enter the deletion routine after 90 days without opening or other recorded activity. Pending payments, paid orders and active generation are excluded from that routine; retention must be limited to what is needed for the order, support, legal obligations or exercising rights. Adults can delete a project and its files in My orders; running tasks must finish or be stopped first. Deleting a project does not delete the Clerk account or a reusable voice saved to the account. Request deletion of these voices or account closure through our privacy contact. Backups, previous file versions and information already received by providers may require additional steps and time. We will explain the scope, applicable timelines and any required retention when handling your request.",
    },
    { type: "h", text: "Your rights" },
    {
      type: "p",
      text: "Under applicable law, you may request confirmation of processing, access and correction; information about sharing; anonymization, restriction or deletion of unnecessary or unlawfully processed information; portability under applicable rules; withdrawal of consent and deletion of consent-based information, subject to lawful retention exceptions. You may also ask about declining consent and its consequences and complain to the Brazilian ANPD where applicable. Requests are free and can be sent to info@storyrus.ai. We may request only the information needed to confirm your identity and authority to act for the person concerned. Applicable response periods and legal limits will be explained. Withdrawal stops the further uses it covers but does not automatically undo prior processing or an already fulfilled order.",
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
      text: "We may update this policy. The date at the top identifies the text version. Material changes may be posted on the site or sent by email. A new purpose requiring consent must be explained and authorized separately.",
    },
    {"type":"h","text":"Adult authorization and control"},
    {"type":"p","text":"Before uploading photos, the adult must read the notice and confirm authorization to create the book. We record the notice version, time, account and purpose. In My orders you can withdraw authorization for further uses of the photos; this is different from deleting a project. The authorization does not permit publishing the files or using them for advertising. Upload a child's information only as their legal guardian or with that guardian's authorization. Contact info@storyrus.ai for additional requests."},
    {"type":"h","text":"Image processing and sensitive information"},
    {"type":"p","text":"Photos may undergo automated processing and similarity comparison to maintain appearance in illustrations. This does not verify the adult's identity or age. A child's identity documents, precise location, school and health information are not needed for a book. Use a first name or nickname and the age needed for the story."},
    { type: "h", text: "Session, Preferences And Browser Services" },
    { type: "p", text: "Your browser may keep session information and language and appearance preferences in cookies or local storage. Without a saved language preference, ipapi.co is queried to suggest a language from the IP country; that service receives technical connection information. You can change the language manually. Site fonts are loaded from Google Fonts, which also receives the technical information needed for the connection. Clearing browser data may end your session or remove preferences but does not delete projects stored in your account." },
    { type: "h", text: "Access And Security" },
    { type: "p", text: "Project access depends on the account and service permissions; authorized staff may access projects for operation and support. Files are provided through temporary access links when that storage mechanism is used. Do not publish or share private links. No system offers absolute security; report suspected unauthorized access through our privacy contact." },
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
  updated: "Última actualización: 2 de noviembre de 2026.",
  home: "Inicio",
  back: "Volver al inicio",
  blocks: [
    {
      type: "p",
      text: "Story R Us (storyrus.ai) crea libros ilustrados personalizados con datos y fotos enviados por un adulto responsable. Esta política explica qué tratamos, por qué y cómo ejercer tus derechos. La LGPD brasileña y otras normas se aplican según el caso; la sección sobre menores explica el modelo del servicio y las consideraciones sobre la COPPA de Estados Unidos.",
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
        "Cuenta del adulto: la autenticación actual se realiza mediante Clerk. Conservamos correo, identificador de cuenta, nombre, teléfono, dirección facilitada, fecha de registro y constancias de aceptación y declaración de mayoría de edad.",
        "Proyecto: nombre o apodo, edad, dedicatoria, fotos de los personajes, tema, estilo, instrucciones, aprobaciones y archivos generados, como ilustraciones, páginas y PDF.",
        "Pedido: formato, acabado, cantidad, destinatario, entrega, cotización, estado del pago e historial de atención, cuando corresponda.",
        "Uso técnico: información de sesión, preferencias de idioma y apariencia, IP y registros necesarios para la operación y seguridad. Los recursos opcionales de audio y vídeo, cuando estén disponibles y se soliciten, se explican por separado más abajo.",
      ],
    },
    { type: "h", text: "Para qué los usamos" },
    {
      type: "p",
      text: "Usamos los datos necesarios para crear y entregar el libro, mantener la cuenta, enviar comunicaciones del servicio, atender solicitudes y preparar la impresión y entrega solicitadas. La autorización del Estudio cubre el libro; no autoriza automáticamente voz, vídeo, publicación ni publicidad. No vendemos datos personales, no hacemos publicidad segmentada ni usamos los archivos enviados para nuestra propia promoción o entrenamiento de modelos.",
    },
    { type: "h", text: "Finalidades Y Bases Legales" },
    { type: "p", text: "Tratamos los datos de cuenta y pedido para prestar el servicio y ejecutar el contrato. Podemos conservar información para cumplir obligaciones legales o ejercer derechos. El uso de las fotos en el libro exige la autorización específica que se presenta al adulto antes del envío. El consentimiento puede retirarse cuando sea la base del tratamiento. Los datos de menores requieren atención a su interés superior; la declaración de mayoría de edad del adulto no elimina esa protección. La LGPD brasileña se aplica cuando corresponda." },
    { type: "h", text: "Proveedores" },
    {
      type: "p",
      text: "Cuando la generación con IA esté disponible y se solicite, las fotos, características y textos necesarios pueden ser procesados por OpenAI. Clerk gestiona el acceso; el sitio y la API usan Vercel y Render, y los archivos pueden almacenarse en servicios compatibles con S3, incluido Cloudflare R2. Los proveedores de correo, pago, impresión y entrega reciben lo necesario para la etapa solicitada. El modo de prueba genérico identificado en el Estudio no llama a proveedores de IA para generar su contenido. La conservación y demás condiciones de cada proveedor dependen del servicio contratado; contacta con nosotros para más información.",
    },
    { type: "h", text: "Voz Y Vídeo Opcionales" },
    { type: "p", text: "Crear el libro no requiere enviar voz ni pedir un vídeo. Si estos recursos están disponibles, la muestra de voz debe ser del propio adulto y exige autorización específica al enviarla; el audio puede ser procesado por ElevenLabs. El contenido necesario para un vídeo solicitado puede ser procesado por Kling. La autorización de fotos para el libro no sustituye la información ni la autorización exigidas para una finalidad adicional. Los archivos anteriores de estos recursos y las voces guardadas en la cuenta siguen sujetos a esta política." },
    { type: "h", text: "Transferencias Internacionales De Datos" },
    { type: "p", text: "Los proveedores pueden tratar datos fuera de Brasil. Los requisitos de la LGPD sobre transferencias internacionales se aplican cuando corresponda. Puedes solicitar información sobre países, destinatarios y garantías de la operación mediante el contacto de privacidad. Crear una cuenta o aceptar esta política no equivale a autorizar de forma genérica cualquier transferencia o nueva finalidad." },
    { type: "h", text: "Usuarios Internacionales" },
    { type: "p", text: "Puedes indicar una dirección fuera de Brasil. La disponibilidad del servicio digital, impresión y entrega depende de los recursos y socios disponibles. Revisa las condiciones antes de confirmar el pedido y cualquier cobro." },
    { type: "h", text: "Conservación y eliminación" },
    {
      type: "p",
      text: "Los proyectos sin pago entran en la rutina de eliminación tras 90 días sin abrirse ni otra actividad registrada. Los pagos pendientes, pedidos pagados y generaciones activas quedan fuera de esa rutina; la conservación debe limitarse a lo necesario para el pedido, atención, obligaciones legales o ejercicio de derechos. El adulto puede borrar el proyecto y sus archivos en Mis pedidos; las tareas activas deben terminar o interrumpirse antes. Borrar un proyecto no elimina la cuenta de Clerk ni una voz reutilizable guardada en la cuenta. Solicita la eliminación de esas voces o el cierre de cuenta mediante el contacto de privacidad. Las copias de seguridad, versiones anteriores y datos recibidos por proveedores pueden exigir pasos y plazos adicionales. Al atender la solicitud, informaremos sobre alcance, plazos aplicables y cualquier conservación necesaria.",
    },
    { type: "h", text: "Tus Derechos" },
    { type: "p", text: "Según la legislación aplicable, puedes solicitar confirmación del tratamiento, acceso y corrección; información sobre cesiones; anonimización, bloqueo o eliminación de datos innecesarios o tratados irregularmente; portabilidad conforme a la regulación; retirada del consentimiento y eliminación de datos tratados con esa base, salvo conservación legal. También puedes preguntar por la posibilidad de no consentir y sus consecuencias y reclamar ante la ANPD brasileña cuando corresponda. Las solicitudes son gratuitas y pueden enviarse a info@storyrus.ai. Solo pediremos lo necesario para verificar tu identidad y autoridad para actuar por el titular. Informaremos los plazos y límites legales aplicables. Retirar el consentimiento impide los nuevos usos que abarque, pero no deshace automáticamente tratamientos previos ni un pedido ya ejecutado." },
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
    {"type":"p","text":"Antes de enviar fotos, el adulto debe leer el aviso y confirmar la autorización para crear el libro. Registramos versión, momento, cuenta y finalidad. En Mis pedidos puedes retirar la autorización para nuevos usos de las fotos; es una acción distinta de borrar el proyecto. La autorización no permite publicar archivos ni usarlos en publicidad. Envía datos de un menor solo si eres su representante legal o tienes su autorización. Para otras solicitudes, escribe a info@storyrus.ai."},
    {"type":"h","text":"Tratamiento de imágenes e información sensible"},
    {"type":"p","text":"Las fotos pueden procesarse automáticamente y compararse para conservar la apariencia en las ilustraciones. Esto no verifica la identidad ni la edad del adulto. No necesitamos documentos, ubicación exacta, escuela o datos de salud del menor. Usa el nombre o apodo y la edad necesaria para la historia."},
    { type: "h", text: "Sesión, Preferencias Y Servicios Del Navegador" },
    { type: "p", text: "El navegador puede guardar información de sesión y preferencias de idioma y apariencia en cookies o almacenamiento local. Sin una preferencia de idioma guardada, se consulta ipapi.co para sugerir el idioma según el país de la IP; ese servicio recibe los datos técnicos de la conexión. Puedes cambiar el idioma manualmente. Las fuentes se cargan desde Google Fonts, que también recibe los datos técnicos necesarios para la conexión. Borrar los datos del navegador puede cerrar la sesión o eliminar preferencias, pero no borra los proyectos guardados en la cuenta." },
    { type: "h", text: "Acceso Y Seguridad" },
    { type: "p", text: "El acceso a proyectos depende de la cuenta y los permisos del servicio; el personal autorizado puede acceder para operación y atención. Los archivos se facilitan mediante enlaces temporales cuando se utiliza ese mecanismo de almacenamiento. No publiques ni compartas enlaces privados. Ningún sistema ofrece seguridad absoluta; comunica posibles accesos indebidos mediante nuestro contacto de privacidad." },
    { type: "h", text: "Cambios" },
    { type: "p", text: "Podemos actualizar esta política. La fecha al inicio indica la versión del texto. Los cambios relevantes pueden comunicarse en el sitio o por correo. Una nueva finalidad que requiera consentimiento debe informarse y autorizarse por separado." },
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
