export type StudioLang = "pt" | "en" | "es";

type Preset = { title: string; theme: string };

/** Tema do banner sem um livro único: título e história prontos, ainda editáveis. */
const PRESETS: Record<string, Record<StudioLang, Preset>> = {
  adventure: {
    pt: { title: "Uma Grande Aventura", theme: "Aventura: explorar, descobrir e voltar para casa com uma história só da criança." },
    en: { title: "A Great Adventure", theme: "Adventure: exploring, discovering and coming home with a story just for the child." },
    es: { title: "Una Gran Aventura", theme: "Aventura: explorar, descubrir y volver a casa con una historia solo del niño." },
  },
  fantasy: {
    pt: { title: "Uma História de Fantasia", theme: "Fantasia: magia, coragem e um mundo imaginário, com a criança como protagonista." },
    en: { title: "A Fantasy Story", theme: "Fantasy: magic, courage and an imaginary world, with the child as the hero." },
    es: { title: "Una Historia de Fantasía", theme: "Fantasía: magia, coraje y un mundo imaginario, con el niño como protagonista." },
  },
  dinosaurs: {
    pt: { title: "Na Terra dos Dinossauros", theme: "Dinossauros: fósseis, amigos gigantes e coragem numa expedição pré-histórica." },
    en: { title: "In the Land of Dinosaurs", theme: "Dinosaurs: fossils, giant friends and courage on a prehistoric expedition." },
    es: { title: "En la Tierra de los Dinosaurios", theme: "Dinosaurios: fósiles, amigos gigantes y coraje en una expedición prehistórica." },
  },
  underwater: {
    pt: { title: "Os Segredos do Fundo do Mar", theme: "Fundo do Mar: tartarugas, corais e amizade, explorando o oceano com cuidado." },
    en: { title: "Secrets of the Deep Sea", theme: "Under the Sea: turtles, coral and friendship, exploring the ocean with care." },
    es: { title: "Los Secretos del Fondo del Mar", theme: "Fondo del Mar: tortugas, corales y amistad, explorando el océano con cuidado." },
  },
  space: {
    pt: { title: "Uma Aventura Pelo Espaço", theme: "Espaço: foguetes, planetas e curiosidade, com a criança no comando da viagem." },
    en: { title: "A Space Adventure", theme: "Space: rockets, planets and curiosity, with the child leading the journey." },
    es: { title: "Una Aventura Por el Espacio", theme: "Espacio: cohetes, planetas y curiosidad, con el niño al mando del viaje." },
  },
  princess: {
    pt: { title: "Uma História de Princesas", theme: "Princesas: coragem, castelo e um final feliz, com a criança como protagonista." },
    en: { title: "A Princess Story", theme: "Princesses: courage, a castle and a happy ending, with the child as the hero." },
    es: { title: "Una Historia de Princesas", theme: "Princesas: coraje, castillo y un final feliz, con el niño como protagonista." },
  },
  superhero: {
    pt: { title: "Uma Pequena Grande Heroína", theme: "Super-heróis: capa ao vento e coragem no peito, salvando o dia com o coração." },
    en: { title: "A Little Great Hero", theme: "Superheroes: cape in the wind and courage in the heart, saving the day with kindness." },
    es: { title: "Una Pequeña Gran Heroína", theme: "Superhéroes: capa al viento y coraje en el pecho, salvando el día con el corazón." },
  },
  sport: {
    pt: { title: "Uma História de Esporte", theme: "Esporte: treino, coragem e superação, com a criança no centro da própria história." },
    en: { title: "A Sports Story", theme: "Sports: practice, courage and grit, with the child at the center of the story." },
    es: { title: "Una Historia de Deporte", theme: "Deporte: entrenamiento, coraje y superación, con el niño en el centro de la historia." },
  },
  mothers_day: {
    pt: { title: "Uma História de Amor de Mãe", theme: "Dia das Mães: colo, ternura e o carinho da mamãe em cada página." },
    en: { title: "A Story of a Mother's Love", theme: "Mother's Day: hugs, tenderness and mom's love on every page." },
    es: { title: "Una Historia de Amor de Mamá", theme: "Día de la Madre: abrazos, ternura y el cariño de mamá en cada página." },
  },
  fathers_day: {
    pt: { title: "Aventuras com o Papai", theme: "Dia dos Pais: mão na mão com o papai, cada caminho vira uma memória." },
    en: { title: "Adventures with Dad", theme: "Father's Day: hand in hand with dad, every path becomes a memory." },
    es: { title: "Aventuras con Papá", theme: "Día del Padre: de la mano con papá, cada camino se vuelve un recuerdo." },
  },
  grandparents_love: {
    pt: { title: "Uma História de Bisavó", theme: "Vovó e eu: colo, carinho e histórias que atravessam gerações." },
    en: { title: "A Great-Grandparent Story", theme: "Grandma and me: hugs, warmth and stories that cross generations." },
    es: { title: "Una Historia de Bisabuela", theme: "Abuela y yo: abrazos, cariño e historias que cruzan generaciones." },
  },
  grandfather_love: {
    pt: { title: "Uma História de Avô", theme: "Vovô e eu: o colo do avô, o lago e um abraço que não acaba." },
    en: { title: "A Grandpa Story", theme: "Grandpa and me: grandpa's arms, the lake and a hug that never ends." },
    es: { title: "Una Historia de Abuelo", theme: "Abuelo y yo: los brazos del abuelo, el lago y un abrazo que no se acaba." },
  },
  recem_nascidos: {
    pt: { title: "Uma História de Recém-nascido", theme: "Recém-nascidos: os primeiros dias, o colo e o carinho de quem acaba de chegar." },
    en: { title: "A Newborn Story", theme: "Newborns: the first days, a hug and the warmth of someone who has just arrived." },
    es: { title: "Una Historia de Recién Nacido", theme: "Recién nacidos: los primeros días, el abrazo y el cariño de quien acaba de llegar." },
  },
  casamento: {
    pt: { title: "Uma História de Casamento", theme: "Casamento: a criança no centro de uma celebração de amor, votos e família." },
    en: { title: "A Wedding Story", theme: "Wedding: the child at the center of a celebration of love, vows and family." },
    es: { title: "Una Historia de Boda", theme: "Boda: el niño en el centro de una celebración de amor, votos y familia." },
  },
  pets: {
    pt: { title: "Uma História com o Pet", theme: "Pets: o carinho do animal de estimação, cuidado e companhia numa história só da criança." },
    en: { title: "A Story with a Pet", theme: "Pets: a pet's affection, care and company in a story just for the child." },
    es: { title: "Una Historia con la Mascota", theme: "Mascotas: el cariño de la mascota, cuidado y compañía en una historia solo del niño." },
  },
  family_love: {
    pt: { title: "Uma História da Nossa Família", theme: "Família: o carinho de quem ama a criança, reunido numa história só deles." },
    en: { title: "A Story of Our Family", theme: "Family: the love around the child, gathered in a story of their own." },
    es: { title: "Una Historia de Nuestra Familia", theme: "Familia: el cariño de quienes aman al niño, reunido en una historia solo de ellos." },
  },
  christmas: {
    pt: { title: "Um Natal em Família", theme: "Natal: luzes, abraço e o carinho da família para guardar para sempre." },
    en: { title: "A Family Christmas", theme: "Christmas: lights, a hug and the family's warmth to treasure forever." },
    es: { title: "Una Navidad en Familia", theme: "Navidad: luces, un abrazo y el cariño de la familia para guardar siempre." },
  },
  birthday: {
    pt: { title: "Um Aniversário Especial", theme: "Aniversário: velas, abraços e um pedido no coração, numa história só da criança." },
    en: { title: "A Special Birthday", theme: "Birthday: candles, hugs and a wish from the heart, in a story just for the child." },
    es: { title: "Un Cumpleaños Especial", theme: "Cumpleaños: velas, abrazos y un deseo del corazón, en una historia solo del niño." },
  },
  easter: {
    pt: { title: "Uma História de Páscoa", theme: "Páscoa: encontro, recomeço e uma celebração carinhosa com a criança." },
    en: { title: "An Easter Story", theme: "Easter: gathering, a fresh start and a warm celebration with the child." },
    es: { title: "Una Historia de Pascua", theme: "Pascua: encuentro, un nuevo comienzo y una celebración cariñosa con el niño." },
  },
  childrens_day: {
    pt: { title: "O Dia da Criança", theme: "Dia das Crianças: brincar, descobrir e celebrar a criança como protagonista." },
    en: { title: "Children's Day", theme: "Children's Day: play, discovery and celebrating the child as the hero." },
    es: { title: "El Día del Niño", theme: "Día del Niño: jugar, descubrir y celebrar al niño como protagonista." },
  },
  new_year: {
    pt: { title: "Uma História de Ano Novo", theme: "Ano Novo: desejos, recomeço e uma festa em família com a criança." },
    en: { title: "A New Year Story", theme: "New Year: wishes, a fresh start and a family celebration with the child." },
    es: { title: "Una Historia de Año Nuevo", theme: "Año Nuevo: deseos, un nuevo comienzo y una fiesta en familia con el niño." },
  },
  alfabetizacao_inicial: {
    pt: { title: "Aprendendo o Alfabeto", theme: "Alfabetização: letras e descobertas, brincando para aprender." },
    en: { title: "Learning the Alphabet", theme: "Literacy: letters and discoveries, learning through play." },
    es: { title: "Aprendiendo el Alfabeto", theme: "Alfabetización: letras y descubrimientos, jugando para aprender." },
  },
  pensamento_matematico: {
    pt: { title: "Uma Aventura de Números", theme: "Matemática: contar, comparar e descobrir números brincando." },
    en: { title: "A Numbers Adventure", theme: "Math: counting, comparing and discovering numbers through play." },
    es: { title: "Una Aventura de Números", theme: "Matemáticas: contar, comparar y descubrir números jugando." },
  },
  cores: {
    pt: { title: "Um Mundo de Cores", theme: "Cores: nomear e encontrar as cores numa história leve." },
    en: { title: "A World of Colors", theme: "Colors: naming and finding colors in a gentle story." },
    es: { title: "Un Mundo de Colores", theme: "Colores: nombrar y encontrar los colores en una historia suave." },
  },
  higiene_desfralde: {
    pt: { title: "Aprendendo a Cuidar de Si", theme: "Higiene: rotina, cuidado e autonomia, com carinho e sem pressa." },
    en: { title: "Learning to Take Care", theme: "Hygiene: routine, care and independence, gently and without rush." },
    es: { title: "Aprendiendo a Cuidarse", theme: "Higiene: rutina, cuidado y autonomía, con cariño y sin prisa." },
  },
  vestir_autonomia: {
    pt: { title: "Eu Consigo Me Vestir", theme: "Vestir-se: escolher a roupa e ganhar autonomia, um passo de cada vez." },
    en: { title: "I Can Get Dressed", theme: "Getting dressed: choosing clothes and growing independent, one step at a time." },
    es: { title: "Yo Puedo Vestirme", theme: "Vestirse: elegir la ropa y ganar autonomía, un paso a la vez." },
  },
  animais_sons: {
    pt: { title: "Uma Aventura com os Animais", theme: "Animais: conhecer bichos, sons e cuidar da natureza numa jornada gentil." },
    en: { title: "An Animal Adventure", theme: "Animals: meeting creatures, sounds and caring for nature on a gentle journey." },
    es: { title: "Una Aventura con los Animales", theme: "Animales: conocer bichos, sonidos y cuidar la naturaleza en un viaje amable." },
  },
  transporte_ajudantes: {
    pt: { title: "Os Ajudantes da Cidade", theme: "Transporte: carros, trens e quem ajuda a cidade a funcionar." },
    en: { title: "Helpers of the City", theme: "Transport: cars, trains and the people who help the city work." },
    es: { title: "Los Ayudantes de la Ciudad", theme: "Transporte: autos, trenes y quienes ayudan a que la ciudad funcione." },
  },
  literacia_emocional: {
    pt: { title: "O que Eu Sinto", theme: "Sentimentos: nomear emoções e encontrar um jeito carinhoso de atravessá-las." },
    en: { title: "What I Feel", theme: "Feelings: naming emotions and finding a gentle way through them." },
    es: { title: "Lo que Siento", theme: "Sentimientos: nombrar emociones y encontrar una forma cariñosa de atravesarlas." },
  },
  rotina_dormir: {
    pt: { title: "Hora de Dormir", theme: "Hora de dormir: rotina calma, colo e uma história para fechar o dia." },
    en: { title: "Bedtime", theme: "Bedtime: a calm routine, a hug and a story to end the day." },
    es: { title: "Hora de Dormir", theme: "Hora de dormir: rutina tranquila, un abrazo y una historia para cerrar el día." },
  },
  compartilhar_revezar: {
    pt: { title: "Compartilhar e Revezar", theme: "Compartilhar: dividir, esperar a vez e brincar junto." },
    en: { title: "Sharing and Taking Turns", theme: "Sharing: dividing, waiting for a turn and playing together." },
    es: { title: "Compartir y Turnarse", theme: "Compartir: dividir, esperar el turno y jugar juntos." },
  },
  consciencia_corporal: {
    pt: { title: "Conhecendo o Meu Corpo", theme: "Corpo: perceber o corpo, mover-se e cuidar de si com curiosidade." },
    en: { title: "Getting to Know My Body", theme: "Body: noticing the body, moving and taking care with curiosity." },
    es: { title: "Conociendo Mi Cuerpo", theme: "Cuerpo: notar el cuerpo, moverse y cuidarse con curiosidad." },
  },
  biblico: {
    pt: { title: "Uma História Bíblica", theme: "Bíblico: fé, coragem e cuidado, com a criança no centro da própria história." },
    en: { title: "A Biblical Story", theme: "Biblical: faith, courage and care, with the child at the center of the story." },
    es: { title: "Una Historia Bíblica", theme: "Bíblico: fe, coraje y cuidado, con el niño en el centro de la historia." },
  },
  dia_da_mulher: {
    pt: { title: "Uma História para Elas", theme: "Dia da Mulher: o carinho de mães, avós e tias, numa história só da criança." },
    en: { title: "A Story for the Women", theme: "Women's Day: the love of mothers, grandmothers and aunts, in a story just for the child." },
    es: { title: "Una Historia para Ellas", theme: "Día de la Mujer: el cariño de madres, abuelas y tías, en una historia solo del niño." },
  },
  dia_da_sogra: {
    pt: { title: "Uma História para a Sogra", theme: "Dia da Sogra: gratidão e carinho, numa história para guardar em família." },
    en: { title: "A Story for a Mother-in-Law", theme: "Mother-in-law's Day: gratitude and warmth, in a story the family keeps." },
    es: { title: "Una Historia para la Suegra", theme: "Día de la Suegra: gratitud y cariño, en una historia para guardar en familia." },
  },
  dia_da_familia: {
    pt: { title: "Uma História da Nossa Família", theme: "Dia da Família: quem ama a criança reunido numa história só deles." },
    en: { title: "A Story of Our Family", theme: "Family Day: the people who love the child, gathered in a story of their own." },
    es: { title: "Una Historia de Nuestra Familia", theme: "Día de la Familia: quienes aman al niño, reunidos en una historia solo de ellos." },
  },
  dia_do_irmao: {
    pt: { title: "Uma História de Irmãos", theme: "Dia do Irmão: cumplicidade, cuidado e a amizade que cresce em casa." },
    en: { title: "A Siblings Story", theme: "Siblings' Day: closeness, care and the friendship that grows at home." },
    es: { title: "Una Historia de Hermanos", theme: "Día del Hermano: complicidad, cuidado y la amistad que crece en casa." },
  },
  dia_dos_namorados: {
    pt: { title: "Uma História de Namorados", theme: "Dia dos Namorados: carinho a dois, numa história para guardar junto." },
    en: { title: "A Valentine Story", theme: "Valentine's Day: affection for two, in a story to keep together." },
    es: { title: "Una Historia de Enamorados", theme: "Día de los Enamorados: cariño de a dos, en una historia para guardar juntos." },
  },
  dia_do_amigo: {
    pt: { title: "Uma História de Amigos", theme: "Dia do Amigo: companhia, riso e uma amizade para guardar." },
    en: { title: "A Friendship Story", theme: "Friendship Day: company, laughter and a friendship to keep." },
    es: { title: "Una Historia de Amigos", theme: "Día del Amigo: compañía, risa y una amistad para guardar." },
  },
  tio_tia: {
    pt: { title: "Uma História de Tios", theme: "Dia do Tio e da Tia: colo, riso e um amor que a família guarda." },
    en: { title: "An Aunt and Uncle Story", theme: "Aunt and Uncle's Day: a hug, a laugh and a love the family keeps." },
    es: { title: "Una Historia de Tíos", theme: "Día del Tío y de la Tía: un abrazo, una risa y un amor que la familia guarda." },
  },
  dia_dos_filhos: {
    pt: { title: "Uma História para o Filho", theme: "Dia dos Filhos: a criança como protagonista, numa história só dela." },
    en: { title: "A Story for a Child", theme: "Sons and Daughters Day: the child as the hero of a story of their own." },
    es: { title: "Una Historia para el Hijo", theme: "Día de los Hijos: el niño como protagonista, en una historia solo de él." },
  },
  independencia: {
    pt: { title: "Uma História em Família", theme: "Independência do Brasil: um dia de reunião, com a criança no centro da família." },
    en: { title: "A Family Story", theme: "Brazil's Independence Day: a day together, with the child at the center of the family." },
    es: { title: "Una Historia en Familia", theme: "Independencia de Brasil: un día de reunión, con el niño en el centro de la familia." },
  },
  dia_do_idoso: {
    pt: { title: "Uma História de Avós", theme: "Dia do Idoso: avós e bisavós, colo e histórias que atravessam gerações." },
    en: { title: "A Grandparents Story", theme: "Day of Older Persons: grandparents and great-grandparents, hugs and stories across generations." },
    es: { title: "Una Historia de Abuelos", theme: "Día de las Personas Mayores: abuelos y bisabuelos, abrazos e historias que cruzan generaciones." },
  },
};

export function themePreset(tema: string, lang: StudioLang): Preset | null {
  return PRESETS[tema]?.[lang] ?? null;
}
