import type { Theme } from "../types";
import type { Lang } from "../i18n/lang";

export type StudioCopy = {
  themeToggleAria: string;
  theme: string;
  themeToLight: string;
  themeToDark: string;
  account: string;
  orders: string;
  logout: string;
  upgradeOpen: string;
  upgradeTitle: string;
  upgradeHint: string;
  upgradeEmail: string;
  upgradePassword: string;
  upgradeSubmit: string;
  upgradeSaving: string;
  upgradeLater: string;
  demoBanner: string;
  demoCta: string;
  createTitle: string;
  projectLocked: string;
  slogan: string;
  pickThemes: string;
  pickThemesHint: string;
  groupDatas: string;
  groupEducativo: string;
  nameAgeDedication: string;
  childName: string;
  childNamePh: string;
  childAge: string;
  childAgePh: string;
  bookTitle: string;
  bookTitlePh: string;
  themeFree: string;
  themeFreePh: string;
  themeHint: string;
  photoField: string;
  photoFieldHint: string;
  photoCharacters: string;
  photoCharactersHint: string;
  photoDrop: string;
  photoDropHint: string;
  photoRemove: string;
  photoSelected: (n: number) => string;
  dedication: string;
  dedicationPh: string;
  bookSize: string;
  bookSizeM: string;
  bookSizeP: string;
  quantity: string;
  quantityOne: string;
  quantityCopies: string;
  quantityPackage: string;
  quantityCopiesHint: string;
  quantityPackageHint: string;
  coverType: string;
  coverSoft: string;
  coverHard: string;
  artStyle: string;
  artRealistic: string;
  artCartoon: string;
  chosenBook: string;
  clientTitle: string;
  clientName: string;
  clientNamePh: string;
  clientEmail: string;
  clientEmailPh: string;
  clientPhone: string;
  clientPhonePh: string;
  clientAddress: string;
  clientAddressPh: string;
  clientNotes: string;
  clientNotesPh: string;
  clientContinue: string;
  errClient: string;
  createProject: string;
  errMissingFields: string;
  errPhotoRequired: string;
  metaBookTitle: string;
  howTitle: string;
  how: { t: string; p: string }[];
  projectTitle: string;
  metaTheme: string;
  styleLabel: string;
  statusLabel: string;
  artStyleRealistic: string;
  defaultVoiceName: string;
  consent: string;
  photoSent: string;
  orderSent: string;
  orderFollowup: string;
  previewCta: string;
  previewHint: string;
  previewRunning: string;
  previewBuilding: string;
  previewStay: string;
  previewEta: (min: number, max: number) => string;
  previewReadyCue: string;
  previewReadyTitle: string;
  previewStepCharacter: string;
  previewStepCharacterHint: string;
  previewStepStory: string;
  previewStepStoryHint: string;
  previewStepImages: string;
  previewStepImagesHint: string;
  previewImageCover: string;
  previewImagePage: string;
  previewImageHand: string;
  previewImageBook: string;
  previewMustMove: string;
  previewStepWait: string;
  previewStepQueued: string;
  previewStepNow: string;
  previewStepDone: string;
  previewElapsed: (totalSeconds: number) => string;
  previewRetry: string;
  previewTrioTitle: string;
  previewTrioHint: string;
  previewCover: string;
  previewPage: string;
  previewInHand: string;
  changesTitle: string;
  photoChanges: string;
  photoChangesPh: string;
  submitChanges: string;
  changesReceived: string;
  storyPagesTitle: string;
  otherCharacters: string;
  otherCharactersPh: string;
  otherCharactersHint: string;
  gender: string;
  genderF: string;
  genderM: string;
  errGender: string;
  sendPhoto: string;
  photoHint: string;
  extraCharsTitle: string;
  extraCharNamePh: string;
  add: string;
  extrasAdded: (n: number) => string;
  generateExtras: string;
  storyTitle: string;
  inventAi: string;
  writeMine: string;
  sendFile: string;
  readyStories: string;
  generateStory: string;
  loadingCatalog: string;
  needChildName: string;
  catalogMeta: (tematica: string, idade: string, paginas: number, genero?: string) => string;
  applied: string;
  use: string;
  free: string;
  fileHint: string;
  storyPlaceholder: string;
  saveStory: string;
  approveCharacterFirst: string;
  extrasResult: string;
  videoTitle: string;
  videoHint: string;
  animationTitle: string;
  narratedTitle: string;
  newProject: string;
  createMyStory: string;
  errConsentPhoto: string;
  errConsentExtra: string;
  errConsentVoice: string;
  langAria: string;
  ariaPhotoGroup: string;
  ariaSelectPhoto: string;
  ariaSelectExtraPhoto: string;
  ariaExtraCharName: string;
  ariaCatalog: string;
  ariaStoryFile: string;
  ariaStoryText: string;
  ariaResults: string;
  ariaAnimationGenerated: string;
  ariaNarratedGenerated: string;
  ariaCharacterActions: string;
  ariaEbookPages: string;
  ariaBookActions: string;
  ariaVoiceName: string;
  ariaSendAudioClone: string;
  ariaSelectVoice: string;
  ariaProgress: string;
  ariaEbookStep: string;
  ariaVideoSteps: string;
  voiceTitle: string;
  voiceUnavailable: string;
  voiceHint: string;
  voiceNamePh: string;
  cloning: string;
  sendAudio: string;
  voiceAuto: string;
  voiceDefault: string;
  removeVoice: string;
  character: string;
  characterAlt: string;
  characterApproved: string;
  approveCharacter: string;
  regenerateCharacter: string;
  ebook: string;
  pageAlt: (n: number) => string;
  openEbook: string;
  bookApproved: string;
  approveBook: string;
  regeneratePages: string;
  printTitle: string;
  printRequested: string;
  requestPrint: string;
  illustrating: (done: number, total: number) => string;
  attempt: string;
  stepEbook: string;
  stepEbookHint: string;
  stepVideo: string;
  stepVideoHint: string;
  stepNarrated: string;
  stepNarratedHint: string;
  themes: Record<Theme, string>;
};

const THEMES_PT: Record<Theme, string> = {
  adventure: "Aventura",
  princess: "Princesas",
  superhero: "Super-heróis",
  space: "Espaço",
  underwater: "Fundo do Mar",
  dinosaurs: "Dinossauros",
  fantasy: "Fantasia",
  birthday: "Aniversário",
  christmas: "Natal",
  easter: "Páscoa",
  childrens_day: "Dia das Crianças",
  mothers_day: "Dia das Mães",
  fathers_day: "Dia dos Pais",
  new_year: "Ano Novo",
  alfabetizacao_inicial: "Alfabetização",
  pensamento_matematico: "Matemática",
  cores: "Cores",
  opostos_espacial: "Opostos",
  higiene_desfralde: "Higiene",
  rotina_dormir: "Hora de Dormir",
  alimentacao_saudavel: "Alimentação",
  vestir_autonomia: "Vestir-se Sozinho",
  literacia_emocional: "Sentimentos",
  consciencia_corporal: "Corpo",
  compartilhar_revezar: "Compartilhar",
  animais_sons: "Animais e Sons",
  transporte_ajudantes: "Transporte",
  clima_estacoes: "Clima e Estações",
  biblico: "Bíblico",
  casamento: "Casamento",
  recem_nascidos: "Recém-nascidos",
};

const THEMES_EN: Record<Theme, string> = {
  adventure: "Adventure",
  princess: "Princesses",
  superhero: "Superheroes",
  space: "Space",
  underwater: "Under the Sea",
  dinosaurs: "Dinosaurs",
  fantasy: "Fantasy",
  birthday: "Birthday",
  christmas: "Christmas",
  easter: "Easter",
  childrens_day: "Children's Day",
  mothers_day: "Mother's Day",
  fathers_day: "Father's Day",
  new_year: "New Year",
  alfabetizacao_inicial: "Literacy",
  pensamento_matematico: "Math",
  cores: "Colors",
  opostos_espacial: "Opposites",
  higiene_desfralde: "Hygiene",
  rotina_dormir: "Bedtime",
  alimentacao_saudavel: "Healthy Eating",
  vestir_autonomia: "Getting Dressed",
  literacia_emocional: "Feelings",
  consciencia_corporal: "Body",
  compartilhar_revezar: "Sharing",
  animais_sons: "Animals and Sounds",
  transporte_ajudantes: "Transport",
  clima_estacoes: "Weather and Seasons",
  biblico: "Biblical",
  casamento: "Wedding",
  recem_nascidos: "Newborns",
};

const THEMES_ES: Record<Theme, string> = {
  adventure: "Aventura",
  princess: "Princesas",
  superhero: "Superhéroes",
  space: "Espacio",
  underwater: "Fondo del Mar",
  dinosaurs: "Dinosaurios",
  fantasy: "Fantasía",
  birthday: "Cumpleaños",
  christmas: "Navidad",
  easter: "Pascua",
  childrens_day: "Día del Niño",
  mothers_day: "Día de la Madre",
  fathers_day: "Día del Padre",
  new_year: "Año Nuevo",
  alfabetizacao_inicial: "Alfabetización",
  pensamento_matematico: "Matemáticas",
  cores: "Colores",
  opostos_espacial: "Opuestos",
  higiene_desfralde: "Higiene",
  rotina_dormir: "Hora de Dormir",
  alimentacao_saudavel: "Alimentación",
  vestir_autonomia: "Vestirse Solo",
  literacia_emocional: "Sentimientos",
  consciencia_corporal: "Cuerpo",
  compartilhar_revezar: "Compartir",
  animais_sons: "Animales y Sonidos",
  transporte_ajudantes: "Transporte",
  clima_estacoes: "Clima y Estaciones",
  biblico: "Bíblico",
  casamento: "Boda",
  recem_nascidos: "Recién Nacidos",
};

const pt: StudioCopy = {
  themeToggleAria: "Alternar tema claro/escuro",
  theme: "Tema",
  themeToLight: "Claro",
  themeToDark: "Escuro",
  account: "Minha Conta",
  orders: "Meus Pedidos",
  logout: "Sair",
  upgradeOpen: "Criar Conta",
  upgradeTitle: "Salvar esta sessão",
  upgradeHint:
    "Transforme o convidado em conta real. Seus projetos ficam no mesmo lugar.",
  upgradeEmail: "E-mail",
  upgradePassword: "Senha (Mín. 8)",
  upgradeSubmit: "Criar Conta",
  upgradeSaving: "Salvando…",
  upgradeLater: "Agora não",
  demoBanner: "Você está vendo um exemplo pronto.",
  demoCta: "Criar a minha história",
  createTitle: "Crie a sua história",
  projectLocked: "✓ Projeto criado — os campos ficam travados até você começar um novo livro.",
  slogan: "Compartilhe informações essenciais: indique quem será o protagonista, escolha o título e o tema da história. Disponibilize fotos nítidas e desenvolvemos uma história personalizada com o tema escolhido, transformando a pessoa homenageada em protagonista.",
  pickThemes: "",
  pickThemesHint: "",
  groupDatas: "",
  groupEducativo: "",
  nameAgeDedication: "",
  childName: "Nome do protagonista",
  childNamePh: "Ex.: Lila",
  childAge: "Idade",
  childAgePh: "Ex.: 5",
  bookTitle: "Título do livro",
  bookTitlePh: "Ex.: A Lila e o dragão das estrelas",
  themeFree: "Insira o tema desejado",
  themeFreePh: "Ex.: Matteo e seu Herói Favorito",
  themeHint:
    "Quer incluir mais alguém na história (papai, mamãe, irmãos, o pet da família)? Descreva aqui e envie, no campo de foto abaixo, uma imagem que mostre essas pessoas ou animais.",
  photoField: "Foto do protagonista",
  photoFieldHint: "Envie mais de uma foto.",
  photoCharacters: "Foto de um ou mais personagens",
  photoCharactersHint: "Envie fotos do protagonista da sua história. Escolha quem fará parte do seu livro. Adicione fotos de um ou mais personagens relacionadas à história que deseja criar.",
  photoDrop: "Envie fotos do protagonista da sua história.",
  photoDropHint: "Escolha quem fará parte do seu livro. Adicione fotos de um ou mais personagens relacionadas à história que deseja criar.",
  photoRemove: "Remover",
  photoSelected: (n) => (n === 1 ? "1 foto selecionada. Pode enviar mais." : `${n} fotos selecionadas.`),
  dedication: "Dedicatória (2ª página do livro)",
  dedicationPh: "Ex.: Para a Lila, com todo o amor da mamãe.",
  bookSize: "Tamanho do livro",
  bookSizeM: "M — 20 × 20 cm",
  bookSizeP: "P — 15 × 15 cm",
  quantity: "Quantidade de livros",
  quantityOne: "Único",
  quantityCopies: "Cópias",
  quantityPackage: "Pacote",
  quantityCopiesHint: "Escolha de 2 a 10 exemplares.",
  quantityPackageHint: "Acima de 10 unidades.",
  coverType: "Tipo de capa",
  coverSoft: "Capa Flexível",
  coverHard: "Capa Dura",
  artStyle: "Estilo do livro",
  artRealistic: "Realista",
  artCartoon: "Cartoon",
  chosenBook: "Livro escolhido",
  clientTitle: "Cadastro do cliente",
  clientName: "Nome do cliente",
  clientNamePh: "Ex.: Ana Souza",
  clientEmail: "E-mail",
  clientEmailPh: "Ex.: ana@email.com",
  clientPhone: "Telefone / WhatsApp",
  clientPhonePh: "Ex.: 11 99999-9999",
  clientAddress: "Endereço para entrega",
  clientAddressPh: "Rua, número, bairro e cidade",
  clientNotes: "Observação (opcional)",
  clientNotesPh: "Ex.: entregar à tarde",
  clientContinue: "Continuar para o livro",
  errClient: "Preencha nome, e-mail, telefone e endereço.",
  createProject: "Gerar o livro",
  errMissingFields: "Preencha nome, título, tema e idade antes de continuar.",
  errPhotoRequired: "Selecione a foto do protagonista.",
  metaBookTitle: "Título",
  howTitle: "Como Funciona",
  how: [
    { t: "Preencha os Dados", p: "Envie as informações, escolha o tema da história e envie fotos nítidas relacionadas à história que deseja criar." },
    { t: "Acompanhe a Criação", p: "Criamos o personagem ilustrado com base nas fotos enviadas. Desenvolvemos uma história única e envolvente. Você confere e aprova antes de avançarmos." },
    { t: "Revise e Aprove", p: "Revise a prévia, capa e páginas para aprovação. Após sua confirmação, o livro é enviado para produção." },
  ],
  projectTitle: "Projeto",
  metaTheme: "Tema",
  styleLabel: "Estilo",
  statusLabel: "Status",
  artStyleRealistic: "Rosto realista",
  defaultVoiceName: "Minha voz",
  consent:
    "Declaro ser o responsável legal e autorizo o uso da imagem enviada e, quando aplicável, da voz fornecida exclusivamente para a criação deste livro personalizado. Esses materiais não serão utilizados para divulgação ou publicidade.",
  photoSent: "Foto enviada ✓",
  orderSent: "Projeto criado",
  orderFollowup: "Revise a história e as imagens. Se quiser mudar algo, diga abaixo.",
  previewCta: "Gerar prévia",
  previewHint: "Gera personagem, história e o trio da prévia: capa, 1 página e foto na mão (OpenAI).",
  previewRunning: "Gerando prévia…",
  previewBuilding: "Estamos montando sua prévia…",
  previewStay: "Fique nesta tela. Ela atualiza sozinha.",
  previewEta: (min, max) =>
    min === max
      ? `Previsão: cerca de ${min} ${min === 1 ? "minuto" : "minutos"}.`
      : `Previsão: cerca de ${min} a ${max} minutos.`,
  previewReadyCue: "Ficou pronto quando o título mudar para Prévia pronta e a história e as imagens aparecerem aqui.",
  previewReadyTitle: "Prévia pronta",
  previewStepCharacter: "Personagem",
  previewStepCharacterHint: "A foto vira o personagem ilustrado.",
  previewStepStory: "História",
  previewStepStoryHint: "O texto do livro é escrito com o nome e o tema.",
  previewStepImages: "Imagens",
  previewStepImagesHint: "Saem a capa, uma página e o livro na mão.",
  previewImageCover: "Gerando a capa.",
  previewImagePage: "Gerando a página.",
  previewImageHand: "Gerando o livro na mão.",
  previewImageBook: "Montando o livro.",
  previewMustMove: "Não fica parado. Cada etapa gera a próxima até o livro aparecer.",
  previewStepWait: "Aguardando",
  previewStepQueued: "Na fila",
  previewStepNow: "Agora",
  previewStepDone: "Pronto",
  previewElapsed: (totalSeconds) => {
    const min = Math.floor(totalSeconds / 60);
    const sec = String(totalSeconds % 60).padStart(2, "0");
    return `Já se passaram ${min}:${sec}.`;
  },
  previewRetry: "Tentar prévia de novo",
  previewTrioTitle: "Prévia do livro",
  previewTrioHint: "Capa, página e foto na mão — como na vitrine.",
  previewCover: "Capa",
  previewPage: "Página",
  previewInHand: "Na mão",
  changesTitle: "Quer alterar algo?",
  photoChanges: "Alterações nas fotos",
  photoChangesPh: "Ex.: trocar a foto do protagonista, incluir o irmão…",
  submitChanges: "Enviar alterações",
  changesReceived: "Recebemos seu pedido de alterações.",
  storyPagesTitle: "História",
  otherCharacters: "Outros personagens (opcional)",
  otherCharactersPh: "Ex.: mamãe, irmão, Totó",
  otherCharactersHint: "Nomes separados por vírgula. A criança já entra como protagonista.",
  gender: "Gênero",
  genderF: "Feminino",
  genderM: "Masculino",
  errGender: "Escolha se é feminino ou masculino.",
  sendPhoto: "Enviar foto",
  photoHint:
    "Melhor resultado: foto nítida, bem iluminada, um rosto de frente, testa e cabelo visíveis. Evite close de cima, de lado ou rosto tapado. A arte é fotográfica, com a criança igual à foto — o mesmo personagem nas páginas e no vídeo.",
  extraCharsTitle: "Personagens Extras (amigos, irmãos, etc.)",
  extraCharNamePh: "Nome do personagem",
  add: "Adicionar",
  extrasAdded: (n) => `${n} personagem(ns) extra(s) adicionado(s)`,
  generateExtras: "Gerar ilustrações dos extras",
  storyTitle: "História",
  inventAi: "✨ Inventar com IA",
  writeMine: "✍️ Escrever a minha",
  sendFile: "📄 Enviar arquivo",
  readyStories: "📚 Histórias prontas",
  generateStory: "Gerar história com IA",
  loadingCatalog: "Carregando catálogo…",
  needChildName: "Defina o nome da criança ao criar o projeto — ele entra no título e no texto.",
  catalogMeta: (tematica, idade, paginas, genero) =>
    `${tematica} · ${idade} anos · ${paginas} páginas${genero && genero !== "unissex" ? ` · ${genero}` : ""}`,
  applied: "✓ Aplicada",
  use: "Usar",
  free: " (grátis)",
  fileHint: "PDF, DOCX ou TXT (até 5MB)",
  storyPlaceholder:
    "Escreva ou cole a sua história aqui. Dica: separe as páginas com 'Página 1:', 'Página 2:'...",
  saveStory: "Salvar história",
  approveCharacterFirst: "Aprove o personagem para montar o e-book.",
  extrasResult: "Personagens Extras",
  videoTitle: "Vídeo",
  videoHint: "O clipe e o vídeo narrado usam o mesmo personagem 3D do livro.",
  animationTitle: "Animação",
  narratedTitle: "Vídeo narrado",
  newProject: "← Novo projeto",
  createMyStory: "← Criar a minha história",
  errConsentPhoto: "Marque o consentimento para enviar a foto.",
  errConsentExtra: "Marque o consentimento para enviar a foto do personagem extra.",
  errConsentVoice: "Marque o consentimento para clonar a voz.",
  langAria: "Idioma / Language / Idioma",
  ariaPhotoGroup: "Foto do protagonista",
  ariaSelectPhoto: "Selecionar foto do protagonista",
  ariaSelectExtraPhoto: "Selecionar foto do personagem extra",
  ariaExtraCharName: "Nome do personagem extra",
  ariaCatalog: "Catálogo de histórias prontas",
  ariaStoryFile: "Enviar arquivo de história (PDF, DOCX ou TXT)",
  ariaStoryText: "Texto da história",
  ariaResults: "Resultados do projeto",
  ariaAnimationGenerated: "Animação gerada",
  ariaNarratedGenerated: "Vídeo narrado gerado",
  ariaCharacterActions: "Ações do personagem",
  ariaEbookPages: "Páginas do e-book",
  ariaBookActions: "Ações do livro",
  ariaVoiceName: "Nome da voz",
  ariaSendAudioClone: "Enviar áudio para clonar voz",
  ariaSelectVoice: "Selecionar voz da narração",
  ariaProgress: "Progresso das etapas",
  ariaEbookStep: "Etapa do e-book",
  ariaVideoSteps: "Etapas de vídeo",
  voiceTitle: "Voz da narração",
  voiceUnavailable:
    "Voz personalizada indisponível (ElevenLabs não configurado). O vídeo narrado usará a narração padrão.",
  voiceHint:
    "Envie 30–60s de fala clara (MP3, WAV ou M4A), sem música de fundo. Fale naturalmente, como se estivesse contando uma história. A voz fica salva e pode ser reutilizada.",
  voiceNamePh: "Nome da voz",
  cloning: "Clonando...",
  sendAudio: "Enviar áudio",
  voiceAuto: "Automática (padrão da conta ou sistema)",
  voiceDefault: " (padrão)",
  removeVoice: "Remover voz",
  character: "Personagem",
  characterAlt: "Personagem gerado",
  characterApproved: "Personagem aprovado. Pode montar o livro.",
  approveCharacter: "Aprovar personagem",
  regenerateCharacter: "Regenerar personagem",
  ebook: "E-book",
  pageAlt: (n) => `Página ${n}`,
  openEbook: "📖 Abrir e-book",
  bookApproved: "Livro aprovado. PDF, impressão e vídeo liberados.",
  approveBook: "Aprovar livro",
  regeneratePages: "Regenerar páginas",
  printTitle: "Livro impresso",
  printRequested:
    "Pedido registrado. O impresso é cobrado pelo tamanho e pelo frete. O parcelamento no cartão abre quando o pagamento estiver ligado.",
  requestPrint: "Pedir livro impresso",
  illustrating: (done, total) => `Ilustrando ${done}/${total}`,
  attempt: "tent.",
  stepEbook: "Montar ebook",
  stepEbookHint: "E-book ilustrado (precisa de personagem aprovado + história).",
  stepVideo: "Gerar animação",
  stepVideoHint: "Clipe curto (5–10s) com movimento — não é o vídeo narrado.",
  stepNarrated: "Gerar vídeo narrado",
  stepNarratedHint: "História com narração (~1–2 min) a partir do storyboard.",
  themes: THEMES_PT,
};

const en: StudioCopy = {
  themeToggleAria: "Toggle light/dark theme",
  theme: "Theme",
  themeToLight: "Light",
  themeToDark: "Dark",
  account: "My Account",
  orders: "My Orders",
  logout: "Log Out",
  upgradeOpen: "Create Account",
  upgradeTitle: "Save this session",
  upgradeHint:
    "Turn the guest into a real account. Your projects stay in the same place.",
  upgradeEmail: "Email",
  upgradePassword: "Password (Min. 8)",
  upgradeSubmit: "Create Account",
  upgradeSaving: "Saving…",
  upgradeLater: "Not now",
  demoBanner: "You are viewing a ready-made example.",
  demoCta: "Create my story",
  createTitle: "Create your story",
  projectLocked: "✓ Project created — fields stay locked until you start a new book.",
  slogan: "Share the essentials: say who the main character will be, and choose the title and theme. Send clear photos and we create a personalized story on that theme, with the person you honor as the hero.",
  pickThemes: "",
  pickThemesHint: "",
  groupDatas: "",
  groupEducativo: "",
  nameAgeDedication: "",
  childName: "Protagonist's name",
  childNamePh: "e.g. Lila",
  childAge: "Age",
  childAgePh: "e.g. 5",
  bookTitle: "Book title",
  bookTitlePh: "e.g. Lila and the star dragon",
  themeFree: "Enter the desired theme",
  themeFreePh: "e.g. Matteo and his Favorite Hero",
  themeHint:
    "Want to include someone else in the story (dad, mom, siblings, the family pet)? Describe it here and upload a photo below that shows them.",
  photoField: "Hero photo",
  photoFieldHint: "Send more than one photo.",
  photoCharacters: "Photo of one or more characters",
  photoCharactersHint: "Send photos of your story's main character. Choose who will be in your book. Add photos of one or more characters related to the story you want to create.",
  photoDrop: "Send photos of your story's main character.",
  photoDropHint: "Choose who will be in your book. Add photos of one or more characters related to the story you want to create.",
  photoRemove: "Remove",
  photoSelected: (n) => (n === 1 ? "1 photo selected. You can add more." : `${n} photos selected.`),
  dedication: "Dedication (book page 2)",
  dedicationPh: "e.g. For Lila, with all of Mom's love.",
  bookSize: "Book size",
  bookSizeM: "M — 20 × 20 cm",
  bookSizeP: "P — 15 × 15 cm",
  quantity: "Number of books",
  quantityOne: "Single",
  quantityCopies: "Copies",
  quantityPackage: "Package",
  quantityCopiesHint: "Choose from 2 to 10 copies.",
  quantityPackageHint: "More than 10 copies.",
  coverType: "Cover type",
  coverSoft: "Softcover",
  coverHard: "Hardcover",
  artStyle: "Book style",
  artRealistic: "Realistic",
  artCartoon: "Cartoon",
  chosenBook: "Chosen book",
  clientTitle: "Client details",
  clientName: "Client name",
  clientNamePh: "e.g. Ana Souza",
  clientEmail: "Email",
  clientEmailPh: "e.g. ana@email.com",
  clientPhone: "Phone / WhatsApp",
  clientPhonePh: "e.g. +1 555 0100",
  clientAddress: "Delivery address",
  clientAddressPh: "Street, number, neighborhood and city",
  clientNotes: "Note (optional)",
  clientNotesPh: "e.g. deliver in the afternoon",
  clientContinue: "Continue to the book",
  errClient: "Fill in name, email, phone, and address.",
  createProject: "Generate the book",
  errMissingFields: "Fill in name, title, theme, and age before continuing.",
  errPhotoRequired: "Select the hero photo.",
  metaBookTitle: "Title",
  howTitle: "How It Works",
  how: [
    { t: "Fill in the Details", p: "Send the information, choose the story theme, and send clear photos related to the story you want to create." },
    { t: "Follow the Creation", p: "We create the illustrated character from the photos you send. We develop a unique, engaging story. You review and approve it before we continue." },
    { t: "Review and Approve", p: "Review the preview, cover, and pages for approval. After you confirm, the book goes to production." },
  ],
  projectTitle: "Project",
  metaTheme: "Theme",
  styleLabel: "Style",
  statusLabel: "Status",
  artStyleRealistic: "Realistic face",
  defaultVoiceName: "My voice",
  consent:
    "I declare that I am the legal guardian and authorize the use of the submitted image and, when applicable, the provided voice exclusively to create this personalized book. These materials will not be used for promotion or advertising.",
  photoSent: "Photo uploaded ✓",
  orderSent: "Project created",
  orderFollowup: "Review the story and images. If you want changes, tell us below.",
  previewCta: "Generate preview",
  previewHint: "Builds character, story, and the preview trio: cover, 1 page, and in-hand photo (OpenAI).",
  previewRunning: "Generating preview…",
  previewBuilding: "We're building your preview…",
  previewStay: "Stay on this screen. It updates on its own.",
  previewEta: (min, max) =>
    min === max
      ? `Estimate: about ${min} ${min === 1 ? "minute" : "minutes"}.`
      : `Estimate: about ${min} to ${max} minutes.`,
  previewReadyCue: "It's ready when the title changes to Preview ready and the story and images show up here.",
  previewReadyTitle: "Preview ready",
  previewStepCharacter: "Character",
  previewStepCharacterHint: "The photo becomes the illustrated character.",
  previewStepStory: "Story",
  previewStepStoryHint: "The book text is written with the name and theme.",
  previewStepImages: "Images",
  previewStepImagesHint: "The cover, one page, and the book in hand are created.",
  previewImageCover: "Creating the cover.",
  previewImagePage: "Creating the page.",
  previewImageHand: "Creating the book in hand.",
  previewImageBook: "Putting the book together.",
  previewMustMove: "It does not sit idle. Each step starts the next until the book appears.",
  previewStepWait: "Waiting",
  previewStepQueued: "Queued",
  previewStepNow: "Now",
  previewStepDone: "Done",
  previewElapsed: (totalSeconds) => {
    const min = Math.floor(totalSeconds / 60);
    const sec = String(totalSeconds % 60).padStart(2, "0");
    return `${min}:${sec} elapsed.`;
  },
  previewRetry: "Retry preview",
  previewTrioTitle: "Book preview",
  previewTrioHint: "Cover, page, and in-hand shot — like the storefront.",
  previewCover: "Cover",
  previewPage: "Page",
  previewInHand: "In hand",
  changesTitle: "Want to change something?",
  photoChanges: "Photo changes",
  photoChangesPh: "e.g. swap the hero photo, include a sibling…",
  submitChanges: "Send changes",
  changesReceived: "We received your change request.",
  storyPagesTitle: "Story",
  otherCharacters: "Other characters (optional)",
  otherCharactersPh: "e.g. mom, brother, Toto",
  otherCharactersHint: "Separate names with commas. The child is already the main character.",
  gender: "Gender",
  genderF: "Female",
  genderM: "Male",
  errGender: "Choose female or male.",
  sendPhoto: "Upload photo",
  photoHint:
    "Best result: sharp, well-lit photo, one front-facing face, forehead and hair visible. Avoid top-down close-ups, side angles, or covered faces. The art is photographic — the same character on pages and in the video.",
  extraCharsTitle: "Extra characters (friends, siblings, etc.)",
  extraCharNamePh: "Character name",
  add: "Add",
  extrasAdded: (n) => `${n} extra character(s) added`,
  generateExtras: "Generate extra illustrations",
  storyTitle: "Story",
  inventAi: "✨ Invent with AI",
  writeMine: "✍️ Write my own",
  sendFile: "📄 Upload file",
  readyStories: "📚 Ready-made stories",
  generateStory: "Generate story with AI",
  loadingCatalog: "Loading catalog…",
  needChildName: "Set the child's name when creating the project — it goes into the title and text.",
  catalogMeta: (tematica, idade, paginas, genero) =>
    `${tematica} · ages ${idade} · ${paginas} pages${genero && genero !== "unissex" ? ` · ${genero}` : ""}`,
  applied: "✓ Applied",
  use: "Use",
  free: " (free)",
  fileHint: "PDF, DOCX or TXT (up to 5MB)",
  storyPlaceholder:
    "Write or paste your story here. Tip: separate pages with 'Page 1:', 'Page 2:'...",
  saveStory: "Save story",
  approveCharacterFirst: "Approve the character to build the e-book.",
  extrasResult: "Extra characters",
  videoTitle: "Video",
  videoHint: "The clip and narrated video use the same 3D character from the book.",
  animationTitle: "Animation",
  narratedTitle: "Narrated video",
  newProject: "← New project",
  createMyStory: "← Create my story",
  errConsentPhoto: "Check the consent box to upload the photo.",
  errConsentExtra: "Check the consent box to upload the extra character photo.",
  errConsentVoice: "Check the consent box to clone the voice.",
  langAria: "Language / Idioma",
  ariaPhotoGroup: "Hero photo",
  ariaSelectPhoto: "Select hero photo",
  ariaSelectExtraPhoto: "Select extra character photo",
  ariaExtraCharName: "Extra character name",
  ariaCatalog: "Ready-made stories catalog",
  ariaStoryFile: "Upload story file (PDF, DOCX or TXT)",
  ariaStoryText: "Story text",
  ariaResults: "Project results",
  ariaAnimationGenerated: "Generated animation",
  ariaNarratedGenerated: "Generated narrated video",
  ariaCharacterActions: "Character actions",
  ariaEbookPages: "E-book pages",
  ariaBookActions: "Book actions",
  ariaVoiceName: "Voice name",
  ariaSendAudioClone: "Upload audio to clone voice",
  ariaSelectVoice: "Select narration voice",
  ariaProgress: "Step progress",
  ariaEbookStep: "E-book step",
  ariaVideoSteps: "Video steps",
  voiceTitle: "Narration voice",
  voiceUnavailable:
    "Custom voice unavailable (ElevenLabs not configured). Narrated video will use the default narration.",
  voiceHint:
    "Upload 30–60s of clear speech (MP3, WAV or M4A), no background music. Speak naturally, as if telling a story. The voice is saved and reusable.",
  voiceNamePh: "Voice name",
  cloning: "Cloning...",
  sendAudio: "Upload audio",
  voiceAuto: "Automatic (account or system default)",
  voiceDefault: " (default)",
  removeVoice: "Remove voice",
  character: "Character",
  characterAlt: "Generated character",
  characterApproved: "Character approved. You can build the book.",
  approveCharacter: "Approve character",
  regenerateCharacter: "Regenerate character",
  ebook: "E-book",
  pageAlt: (n) => `Page ${n}`,
  openEbook: "📖 Open e-book",
  bookApproved: "Book approved. PDF, print, and video unlocked.",
  approveBook: "Approve book",
  regeneratePages: "Regenerate pages",
  printTitle: "Printed book",
  printRequested:
    "Request logged. The printed book is charged by size and shipping. Card installments open when payment is connected.",
  requestPrint: "Request printed book",
  illustrating: (done, total) => `Illustrating ${done}/${total}`,
  attempt: "att.",
  stepEbook: "Build ebook",
  stepEbookHint: "Illustrated e-book (needs approved character + story).",
  stepVideo: "Generate animation",
  stepVideoHint: "Short clip (5–10s) with motion — not the narrated video.",
  stepNarrated: "Generate narrated video",
  stepNarratedHint: "Story with narration (~1–2 min) from the storyboard.",
  themes: THEMES_EN,
};

const es: StudioCopy = {
  themeToggleAria: "Alternar tema claro/oscuro",
  theme: "Tema",
  themeToLight: "Claro",
  themeToDark: "Oscuro",
  account: "Mi Cuenta",
  orders: "Mis Pedidos",
  logout: "Salir",
  upgradeOpen: "Crear Cuenta",
  upgradeTitle: "Guardar esta sesión",
  upgradeHint:
    "Convierte el invitado en una cuenta real. Tus proyectos se quedan en el mismo lugar.",
  upgradeEmail: "Correo",
  upgradePassword: "Contraseña (Mín. 8)",
  upgradeSubmit: "Crear Cuenta",
  upgradeSaving: "Guardando…",
  upgradeLater: "Ahora no",
  demoBanner: "Estás viendo un ejemplo listo.",
  demoCta: "Crear mi historia",
  createTitle: "Crea tu historia",
  projectLocked: "✓ Proyecto creado — los campos quedan bloqueados hasta que inicies un libro nuevo.",
  slogan: "Comparte lo esencial: indica quién será el protagonista y elige el título y el tema. Envía fotos nítidas y creamos una historia personalizada con el tema elegido, convirtiendo a la persona homenajeada en protagonista.",
  pickThemes: "",
  pickThemesHint: "",
  groupDatas: "",
  groupEducativo: "",
  nameAgeDedication: "",
  childName: "Nombre del protagonista",
  childNamePh: "Ej.: Lila",
  childAge: "Edad",
  childAgePh: "Ej.: 5",
  bookTitle: "Título del libro",
  bookTitlePh: "Ej.: Lila y el dragón de las estrellas",
  themeFree: "Ingresa el tema deseado",
  themeFreePh: "Ej.: Matteo y su Héroe Favorito",
  themeHint:
    "¿Quieres incluir a alguien más en la historia (papá, mamá, hermanos, la mascota)? Descríbelo aquí y sube abajo una foto que los muestre.",
  photoField: "Foto del protagonista",
  photoFieldHint: "Envía más de una foto.",
  photoCharacters: "Foto de uno o más personajes",
  photoCharactersHint: "Envía fotos del protagonista de tu historia. Elige quién formará parte de tu libro. Añade fotos de uno o más personajes relacionadas con la historia que quieres crear.",
  photoDrop: "Envía fotos del protagonista de tu historia.",
  photoDropHint: "Elige quién formará parte de tu libro. Añade fotos de uno o más personajes relacionadas con la historia que quieres crear.",
  photoRemove: "Quitar",
  photoSelected: (n) => (n === 1 ? "1 foto seleccionada. Puedes enviar más." : `${n} fotos seleccionadas.`),
  dedication: "Dedicatoria (2.ª página del libro)",
  dedicationPh: "Ej.: Para Lila, con todo el amor de mamá.",
  bookSize: "Tamaño del libro",
  bookSizeM: "M — 20 × 20 cm",
  bookSizeP: "P — 15 × 15 cm",
  quantity: "Cantidad de libros",
  quantityOne: "Único",
  quantityCopies: "Copias",
  quantityPackage: "Paquete",
  quantityCopiesHint: "Elige de 2 a 10 ejemplares.",
  quantityPackageHint: "Más de 10 unidades.",
  coverType: "Tipo de tapa",
  coverSoft: "Tapa Blanda",
  coverHard: "Tapa Dura",
  artStyle: "Estilo del libro",
  artRealistic: "Realista",
  artCartoon: "Cartoon",
  chosenBook: "Libro elegido",
  clientTitle: "Datos del cliente",
  clientName: "Nombre del cliente",
  clientNamePh: "Ej.: Ana Souza",
  clientEmail: "Correo",
  clientEmailPh: "Ej.: ana@email.com",
  clientPhone: "Teléfono / WhatsApp",
  clientPhonePh: "Ej.: 11 99999-9999",
  clientAddress: "Dirección de entrega",
  clientAddressPh: "Calle, número, barrio y ciudad",
  clientNotes: "Observación (opcional)",
  clientNotesPh: "Ej.: entregar por la tarde",
  clientContinue: "Continuar al libro",
  errClient: "Completa nombre, correo, teléfono y dirección.",
  createProject: "Generar el libro",
  errMissingFields: "Completa nombre, título, tema y edad antes de continuar.",
  errPhotoRequired: "Selecciona la foto del protagonista.",
  metaBookTitle: "Título",
  howTitle: "Cómo Funciona",
  how: [
    { t: "Completa los Datos", p: "Envía la información, elige el tema de la historia y envía fotos nítidas relacionadas con la historia que quieres crear." },
    { t: "Acompaña la Creación", p: "Creamos el personaje ilustrado a partir de las fotos enviadas. Desarrollamos una historia única y envolvente. Tú revisas y apruebas antes de que avancemos." },
    { t: "Revisa y Aprueba", p: "Revisa la vista previa, la portada y las páginas para aprobar. Tras tu confirmación, el libro se envía a producción." },
  ],
  projectTitle: "Proyecto",
  metaTheme: "Tema",
  styleLabel: "Estilo",
  statusLabel: "Estado",
  artStyleRealistic: "Rostro realista",
  defaultVoiceName: "Mi voz",
  consent:
    "Declaro ser el responsable legal y autorizo el uso de la imagen enviada y, cuando corresponda, de la voz proporcionada exclusivamente para la creación de este libro personalizado. Estos materiales no se utilizarán para difusión ni publicidad.",
  photoSent: "Foto enviada ✓",
  orderSent: "Proyecto creado",
  orderFollowup: "Revisa la historia y las imágenes. Si quieres cambiar algo, escríbelo abajo.",
  previewCta: "Generar vista previa",
  previewHint: "Genera personaje, historia y el trío de vista previa: portada, 1 página y foto en mano (OpenAI).",
  previewRunning: "Generando vista previa…",
  previewBuilding: "Estamos preparando tu vista previa…",
  previewStay: "Quédate en esta pantalla. Se actualiza sola.",
  previewEta: (min, max) =>
    min === max
      ? `Previsión: unos ${min} ${min === 1 ? "minuto" : "minutos"}.`
      : `Previsión: unos ${min} a ${max} minutos.`,
  previewReadyCue: "Está lista cuando el título cambie a Vista previa lista y aparezcan aquí la historia y las imágenes.",
  previewReadyTitle: "Vista previa lista",
  previewStepCharacter: "Personaje",
  previewStepCharacterHint: "La foto se convierte en el personaje ilustrado.",
  previewStepStory: "Historia",
  previewStepStoryHint: "El texto del libro se escribe con el nombre y el tema.",
  previewStepImages: "Imágenes",
  previewStepImagesHint: "Salen la portada, una página y el libro en la mano.",
  previewImageCover: "Generando la portada.",
  previewImagePage: "Generando la página.",
  previewImageHand: "Generando el libro en la mano.",
  previewImageBook: "Armando el libro.",
  previewMustMove: "No se queda parado. Cada etapa genera la siguiente hasta que aparece el libro.",
  previewStepWait: "En espera",
  previewStepQueued: "En cola",
  previewStepNow: "Ahora",
  previewStepDone: "Listo",
  previewElapsed: (totalSeconds) => {
    const min = Math.floor(totalSeconds / 60);
    const sec = String(totalSeconds % 60).padStart(2, "0");
    return `Ya pasaron ${min}:${sec}.`;
  },
  previewRetry: "Reintentar vista previa",
  previewTrioTitle: "Vista previa del libro",
  previewTrioHint: "Portada, página y foto en mano — como en la vitrina.",
  previewCover: "Portada",
  previewPage: "Página",
  previewInHand: "En mano",
  changesTitle: "¿Quieres cambiar algo?",
  photoChanges: "Cambios en las fotos",
  photoChangesPh: "Ej.: cambiar la foto del protagonista, incluir al hermano…",
  submitChanges: "Enviar cambios",
  changesReceived: "Recibimos tu pedido de cambios.",
  storyPagesTitle: "Historia",
  otherCharacters: "Otros personajes (opcional)",
  otherCharactersPh: "Ej.: mamá, hermano, Totó",
  otherCharactersHint: "Separa los nombres con comas. El niño ya entra como protagonista.",
  gender: "Género",
  genderF: "Femenino",
  genderM: "Masculino",
  errGender: "Elige si es femenino o masculino.",
  sendPhoto: "Enviar foto",
  photoHint:
    "Mejor resultado: foto nítida, bien iluminada, un rostro de frente, frente y cabello visibles. Evita close desde arriba, de lado o rostro tapado. El arte es fotográfico, con el niño/a igual a la foto — el mismo personaje en las páginas y en el video.",
  extraCharsTitle: "Personajes extras (amigos, hermanos, etc.)",
  extraCharNamePh: "Nombre del personaje",
  add: "Añadir",
  extrasAdded: (n) => `${n} personaje(s) extra(s) añadido(s)`,
  generateExtras: "Generar ilustraciones de los extras",
  storyTitle: "Historia",
  inventAi: "✨ Inventar con IA",
  writeMine: "✍️ Escribir la mía",
  sendFile: "📄 Enviar archivo",
  readyStories: "📚 Historias listas",
  generateStory: "Generar historia con IA",
  loadingCatalog: "Cargando catálogo…",
  needChildName: "Define el nombre del niño/a al crear el proyecto — entra en el título y el texto.",
  catalogMeta: (tematica, idade, paginas, genero) =>
    `${tematica} · ${idade} años · ${paginas} páginas${genero && genero !== "unissex" ? ` · ${genero}` : ""}`,
  applied: "✓ Aplicada",
  use: "Usar",
  free: " (gratis)",
  fileHint: "PDF, DOCX o TXT (hasta 5MB)",
  storyPlaceholder:
    "Escribe o pega tu historia aquí. Consejo: separa las páginas con 'Página 1:', 'Página 2:'...",
  saveStory: "Guardar historia",
  approveCharacterFirst: "Aprueba el personaje para montar el e-book.",
  extrasResult: "Personajes extras",
  videoTitle: "Video",
  videoHint: "El clip y el video narrado usan el mismo personaje 3D del libro.",
  animationTitle: "Animación",
  narratedTitle: "Video narrado",
  newProject: "← Nuevo proyecto",
  createMyStory: "← Crear mi historia",
  errConsentPhoto: "Marca el consentimiento para enviar la foto.",
  errConsentExtra: "Marca el consentimiento para enviar la foto del personaje extra.",
  errConsentVoice: "Marca el consentimiento para clonar la voz.",
  langAria: "Idioma / Language",
  ariaPhotoGroup: "Foto del protagonista",
  ariaSelectPhoto: "Seleccionar foto del protagonista",
  ariaSelectExtraPhoto: "Seleccionar foto del personaje extra",
  ariaExtraCharName: "Nombre del personaje extra",
  ariaCatalog: "Catálogo de historias listas",
  ariaStoryFile: "Enviar archivo de historia (PDF, DOCX o TXT)",
  ariaStoryText: "Texto de la historia",
  ariaResults: "Resultados del proyecto",
  ariaAnimationGenerated: "Animación generada",
  ariaNarratedGenerated: "Video narrado generado",
  ariaCharacterActions: "Acciones del personaje",
  ariaEbookPages: "Páginas del e-book",
  ariaBookActions: "Acciones del libro",
  ariaVoiceName: "Nombre de la voz",
  ariaSendAudioClone: "Enviar audio para clonar voz",
  ariaSelectVoice: "Seleccionar voz de la narración",
  ariaProgress: "Progreso de las etapas",
  ariaEbookStep: "Etapa del e-book",
  ariaVideoSteps: "Etapas de video",
  voiceTitle: "Voz de la narración",
  voiceUnavailable:
    "Voz personalizada no disponible (ElevenLabs no configurado). El video narrado usará la narración predeterminada.",
  voiceHint:
    "Envía 30–60s de habla clara (MP3, WAV o M4A), sin música de fondo. Habla con naturalidad, como si contaras una historia. La voz se guarda y se puede reutilizar.",
  voiceNamePh: "Nombre de la voz",
  cloning: "Clonando...",
  sendAudio: "Enviar audio",
  voiceAuto: "Automática (predeterminada de la cuenta o del sistema)",
  voiceDefault: " (predeterminada)",
  removeVoice: "Quitar voz",
  character: "Personaje",
  characterAlt: "Personaje generado",
  characterApproved: "Personaje aprobado. Puedes montar el libro.",
  approveCharacter: "Aprobar personaje",
  regenerateCharacter: "Regenerar personaje",
  ebook: "E-book",
  pageAlt: (n) => `Página ${n}`,
  openEbook: "📖 Abrir e-book",
  bookApproved: "Libro aprobado. PDF, impresión y video liberados.",
  approveBook: "Aprobar libro",
  regeneratePages: "Regenerar páginas",
  printTitle: "Libro impreso",
  printRequested:
    "Pedido registrado. El impreso se cobra por tamaño y envío. El pago en cuotas abre cuando el pago esté conectado.",
  requestPrint: "Pedir libro impreso",
  illustrating: (done, total) => `Ilustrando ${done}/${total}`,
  attempt: "int.",
  stepEbook: "Montar ebook",
  stepEbookHint: "E-book ilustrado (necesita personaje aprobado + historia).",
  stepVideo: "Generar animación",
  stepVideoHint: "Clip corto (5–10s) con movimiento — no es el video narrado.",
  stepNarrated: "Generar video narrado",
  stepNarratedHint: "Historia con narración (~1–2 min) a partir del storyboard.",
  themes: THEMES_ES,
};

export const STUDIO_I18N: Record<Lang, StudioCopy> = { pt, en, es };

export function studioCopy(lang: Lang): StudioCopy {
  return STUDIO_I18N[lang] ?? STUDIO_I18N.pt;
}
