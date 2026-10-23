# Story R Us — Instagram padronizado em 3 idiomas

Guia pronto para montar e operar as **três contas regionais**, todas com a mesma
identidade visual do site **storyrus.ai** (fontes Baloo 2 + Quicksand, paleta azul-marinho
`#1f3568` / amarelo `#f4b740` / creme, capa em formato de livro 3D).

| Conta | Idioma | Público | Link na bio | Pasta de artes |
|---|---|---|---|---|
| **@storyrus.br** | Português (Brasil) | Brasil | storyrus.ai | `docs/social-assets/real/br/` |
| **@storyr.us** | English (US) | EUA / global | storyrus.ai | `docs/social-assets/real/en/` |
| **@storyrus.es** | Español | Espanha / LatAm | storyrus.ai | `docs/social-assets/real/es/` |

Cada pasta tem: `feed/` (10 posts 1:1), `carrossel/` (5 carrosséis 1:1) e `stories/` (6 stories 9:16).

Regerar tudo: `python Storyrus/scripts/build_instagram_posts.py` (gera os 3 idiomas de uma vez).

---

## 1. Nome, @ e foto de perfil (igual nas 3)

- **Foto de perfil:** logo Story R Us sobre fundo creme (`apps/web/src/assets/logo.png`), centralizado.
- **Categoria:** Loja de presentes personalizados / Serviço de livros infantis.
- **Botões de ação:** "Ver loja" / "Shop" → `storyrus.ai`.
- **Nome de exibição (campo pesquisável — inclua palavras-chave):**
  - BR: `Story R Us | Livro infantil personalizado`
  - EN: `Story R Us | Personalized kids' books`
  - ES: `Story R Us | Libro infantil personalizado`

---

## 2. Bios (copiar e colar)

### 🇧🇷 @storyrus.br
```
📖 O livro em que SEU FILHO é o herói
📸 Envie 1 foto → viramos personagem + história
🎁 eBook na hora • livro impresso • vídeo
✨ Crie a prévia GRÁTIS 👇
```
Link: `storyrus.ai`

### 🇺🇸 @storyr.us
```
📖 The book where YOUR CHILD is the hero
📸 Send 1 photo → we create character + story
🎁 Instant eBook • printed book • video
✨ Create your FREE preview 👇
```
Link: `storyrus.ai`

### 🇪🇸 @storyrus.es
```
📖 El libro donde TU HIJO es el héroe
📸 Envía 1 foto → creamos personaje + historia
🎁 eBook al instante • libro impreso • vídeo
✨ Crea tu vista previa GRATIS 👇
```
Link: `storyrus.ai`

> Dica: use um link-in-bio (ou o próprio `storyrus.ai`) apontando para a criação da prévia.

---

## 3. Destaques (Highlights) — nomes + capas

Use as **capas em formato de livro** já geradas (reaproveite os stories como capa de destaque)
ou um ícone simples em azul-marinho sobre creme. Ordem sugerida:

| # | 🇧🇷 BR | 🇺🇸 EN | 🇪🇸 ES |
|---|---|---|---|
| 1 | Como funciona | How it works | Cómo funciona |
| 2 | Temas | Themes | Temas |
| 3 | Antes/Depois | Before/After | Antes/Después |
| 4 | Avaliações | Reviews | Opiniones |
| 5 | Natal 🎄 | Christmas 🎄 | Navidad 🎄 |
| 6 | Dúvidas | FAQ | Preguntas |

Conteúdo de cada destaque = os stories/carrosséis do idioma correspondente
(`story-03-comofunciona`, `c2-temas`, `c4-antesdepois`, `story-05-prova`, `c3-natal`, `c5-faq`).

---

## 4. Grade de feed (mesma ordem nas 3 contas)

| Slot | Arquivo | Conteúdo |
|---|---|---|
| 01 | `feed-01-hero` | Foto de impacto + headline principal |
| 02 | `feed-02-produto` | Como transformamos foto em história |
| 03 | `feed-03-temas` | Grade de 6 temas |
| 04 | `feed-04-natal` | Presente de Natal (com prazo) |
| 05 | `feed-05-blackfriday` | Black Friday |
| 06 | `feed-06-aniversario` | Aniversário |
| 07 | `feed-07-avos` | Para os avós |
| 08 | `feed-08-pets` | Pets |
| 09 | `feed-09-bebe` | Recém-nascido |
| 10 | `feed-10-prova` | Prova social (depoimento) |

Carrosséis: `c1-comofunciona`, `c2-temas`, `c3-natal`, `c4-antesdepois`, `c5-faq`.
Stories: `story-01-cta`, `02-prazo`, `03-comofunciona`, `04-enquete`, `05-prova`, `06-blackfriday`.

---

## 5. Legendas prontas (post a post)

### 🇧🇷 @storyrus.br

**01 • Hero**
```
E se o seu filho fosse o herói de um livro de verdade? 📖✨
Você envia uma foto e a gente cria um personagem com o rostinho dele — numa história só dele.
Crie a prévia grátis (link na bio). 💛
#livroinfantil #presentepersonalizado #storyrus
```
**02 • Produto**
```
Uma foto hoje vira uma memória para a vida toda. 📸➡️📚
Sem precisar desenhar nem usar programa nenhum: você manda a foto, a gente faz o resto.
👉 storyrus.ai
#livropersonalizado #maternidade #presentecriativo
```
**03 • Temas**
```
Espaço, dinossauros, fundo do mar, super-heróis, pets… qual é a cara do seu filho? 🚀🦕
Arrasta pra escolher — ou peça um tema sob medida. 💫
#historiainfantil #presenteparacriança #storyrus
```
**04 • Natal**
```
O presente de Natal que a família guarda para sempre. 🎄
Peça até 15/12 e receba a tempo. 🎁
#natal #presentedenatal #livroinfantil
```
**05 • Black Friday**
```
BLACK FRIDAY chegou! 🖤 Seu livro personalizado com condição especial, só até 29/11.
Garanta o seu antes que acabe 👉 storyrus.ai
#blackfriday #presentepersonalizado
```
**06 • Aniversário**
```
O aniversário dele vira uma história só dele. 🎂📖
Um presente que ninguém esquece. #aniversario #presentecriativo
```
**07 • Avós**
```
O presente que emociona os avós. 💛 Netos e avós na mesma história.
#diadosavos #presenteparaavo #familia
```
**08 • Pets**
```
Seu filho e o melhor amigo na mesma aventura. 🐶 O pet da família também vira personagem!
#pets #petlovers #livroinfantil
```
**09 • Bebê**
```
O primeiro presente que ele guarda para sempre. 🍼 Perfeito para recém-nascidos.
#chadebebe #recemnascido #presentebebe
```
**10 • Prova social**
```
"A reação dela ao se ver no livro não tem preço." ⭐⭐⭐⭐⭐
Crie a prévia grátis e viva isso também. 👉 storyrus.ai
#depoimento #presentepersonalizado
```

### 🇺🇸 @storyr.us

**01 • Hero**
```
What if your child were the hero of a real book? 📖✨
Send one photo and we'll turn them into a character — in a story that's all their own.
Create your free preview (link in bio). 💛
#personalizedbook #kidsbooks #giftsforkids
```
**02 • Product**
```
One photo today becomes a memory for life. 📸➡️📚
No drawing, no software — you send the photo, we do the rest.
👉 storyrus.ai
#custombook #momlife #thoughtfulgifts
```
**03 • Themes**
```
Space, dinosaurs, under the sea, superheroes, pets… what's your child into? 🚀🦕
Swipe to pick — or ask for a custom theme. 💫
#kidsbook #giftsforkids #storyrus
```
**04 • Christmas**
```
The Christmas gift your family keeps forever. 🎄
Order by Dec 15 to get it in time. 🎁
#christmasgift #personalizedgift #kidsbooks
```
**05 • Black Friday**
```
BLACK FRIDAY is here! 🖤 Your personalized book with a special deal — only until Nov 29.
Get yours before it's gone 👉 storyrus.ai
#blackfriday #personalizedgift
```
**06 • Birthday**
```
Their birthday becomes a story all their own. 🎂📖 A gift no one forgets.
#birthdaygift #giftsforkids
```
**07 • Grandparents**
```
The gift that moves grandparents. 💛 Grandkids and grandparents in one story.
#grandparents #familygift #keepsake
```
**08 • Pets**
```
Your child and their best friend in one adventure. 🐶 The family pet becomes a character too!
#petlovers #kidsbook #familygift
```
**09 • Baby**
```
The first gift they keep forever. 🍼 Perfect for newborns.
#babyshower #newborn #babygift
```
**10 • Social proof**
```
"Her reaction to seeing herself in the book is priceless." ⭐⭐⭐⭐⭐
Create your free preview and live it too. 👉 storyrus.ai
#testimonial #personalizedgift
```

### 🇪🇸 @storyrus.es

**01 • Hero**
```
¿Y si tu hijo fuera el héroe de un libro de verdad? 📖✨
Envías una foto y creamos un personaje con su carita — en una historia solo suya.
Crea tu vista previa gratis (link en la bio). 💛
#libropersonalizado #librosinfantiles #regalosparaniños
```
**02 • Producto**
```
Una foto de hoy se convierte en un recuerdo para toda la vida. 📸➡️📚
Sin dibujar ni usar ningún programa: tú envías la foto, nosotros hacemos el resto.
👉 storyrus.ai
#libropersonalizado #maternidad #regaloscreativos
```
**03 • Temas**
```
Espacio, dinosaurios, fondo del mar, superhéroes, mascotas… ¿cómo es tu hijo? 🚀🦕
Desliza para elegir — o pide un tema a medida. 💫
#libroinfantil #regalosparaniños #storyrus
```
**04 • Navidad**
```
El regalo de Navidad que la familia guarda para siempre. 🎄
Pide antes del 15/12 y recíbelo a tiempo. 🎁
#navidad #regalodenavidad #librosinfantiles
```
**05 • Black Friday**
```
¡Llegó el BLACK FRIDAY! 🖤 Tu libro personalizado con una oferta especial, solo hasta el 29/11.
Consigue el tuyo antes de que se acabe 👉 storyrus.ai
#blackfriday #regalopersonalizado
```
**06 • Cumpleaños**
```
Su cumpleaños se convierte en una historia solo suya. 🎂📖 Un regalo que nadie olvida.
#cumpleaños #regalosparaniños
```
**07 • Abuelos**
```
El regalo que emociona a los abuelos. 💛 Nietos y abuelos en la misma historia.
#abuelos #regalofamiliar #recuerdo
```
**08 • Mascotas**
```
Tu hijo y su mejor amigo en la misma aventura. 🐶 ¡La mascota de la familia también es personaje!
#mascotas #libroinfantil #regalofamiliar
```
**09 • Bebé**
```
El primer regalo que guarda para siempre. 🍼 Perfecto para recién nacidos.
#babyshower #reciénnacido #regalobebé
```
**10 • Prueba social**
```
"Su reacción al verse en el libro no tiene precio." ⭐⭐⭐⭐⭐
Crea tu vista previa gratis y vívelo también. 👉 storyrus.ai
#testimonio #regalopersonalizado
```

---

## 6. Blocos de hashtags (copie o bloco do idioma)

**BR:** `#livroinfantil #livropersonalizado #presentepersonalizado #presentecriativo #maternidade #paternidade #presenteparacrianca #historiainfantil #livrodecrianca #storyrus #natal #blackfriday`

**EN:** `#personalizedbook #custombook #kidsbooks #giftsforkids #momlife #thoughtfulgifts #keepsake #childrensbook #personalizedgift #storyrus #christmasgift #blackfriday`

**ES:** `#libropersonalizado #libroinfantil #librosinfantiles #regalopersonalizado #regalosparaniños #maternidad #regaloscreativos #cuentoinfantil #recuerdo #storyrus #navidad #blackfriday`

---

## 7. Calendário de novembro (mesma estrutura, 3 contas)

Publicar sempre no mesmo dia nas três contas, cada uma no seu idioma.

| Semana | Post principal | Story |
|---|---|---|
| 01–03/11 | Hero (01) | CTA (01) |
| 04–07/11 | Produto (02) + Carrossel "Como funciona" | Como funciona (03) |
| 08–11/11 | Temas (03) + Carrossel Temas | Enquete (04) |
| 12–16/11 | Prova social (10) + Carrossel Antes/Depois | Prova (05) |
| 17–21/11 | Avós (07) / Pets (08) | FAQ |
| 22–28/11 | Aquecimento Black Friday | Prazo/Oferta |
| **29/11** | **Black Friday (05)** | **Black Friday (06)** |
| 30/11 | Aniversário (06) + Carrossel FAQ | Enquete |

Depois (dez): foco Natal — post 04 + Carrossel Natal + Story "prazo" reforçando **15/12**.

---

## 8. Observações de identidade

- As capas/fotos usam automaticamente a **versão localizada** (`-en` / `-es`) quando ela existe
  em `apps/web/public/exemplos/`. Onde ainda não há versão traduzida de uma capa específica,
  o gerador usa uma capa equivalente que já tem o texto no idioma (ex.: post "produto" EN/ES
  usa *Nano and his Adventures* em vez da capa "Meu Pai, Meu Herói").
- Datas são automáticas por idioma: BR/ES `29/11` e `15/12`; EN `Nov 29` e `Dec 15`.
  Edite em `DATES` no topo do script e regenere.
- Para trocar textos, edite o dicionário `T` (e as listas `THEMES`, `FAQ`, etc.) no script.
