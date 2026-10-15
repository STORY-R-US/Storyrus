# Story R Us — Mobile (Expo)

App React Native (Expo) alinhado ao web: **conta obrigatória** (login/signup)
antes do estúdio → temas / nome → criar projeto → consentimento + foto →
etapas (avatar, história, ebook, vídeo, **vídeo narrado**) → vozes, aprovações
e pedido de impressão.

## Rodar

```bash
npm install
npm start          # abre o Expo; use o app Expo Go ou um emulador
```

## Apontar para a API

Por padrão `expo.extra.apiBase` aponta para o BFF de produção
`https://storyrus.ai` (API sob `/v1`, same-origin proxy).

Para desenvolvimento local, sobrescreva com a env `EXPO_PUBLIC_API_BASE`
(tem prioridade sobre `app.json`):

```bash
# Emulador Android → host machine
EXPO_PUBLIC_API_BASE=http://10.0.2.2:8000 npx expo start

# Device físico → IP da sua máquina na LAN
EXPO_PUBLIC_API_BASE=http://192.168.0.10:8000 npx expo start
```

Ou edite temporariamente `app.json` → `expo.extra.apiBase`.

O JWT de **conta registrada** é persistido em AsyncStorage (`storyrus_token`).
Convidados não entram no estúdio.

## Estrutura

```
App.tsx              # boot → Auth obrigatório → Studio
src/api.ts           # client REST + ensureSession + AsyncStorage
src/types.ts
src/themes.ts        # catálogo de temas (paridade web)
src/AuthScreen.tsx   # login/signup (wall)
src/StudioScreen.tsx # temas, etapas, aprovações, assets
src/VoicePanel.tsx   # clone / seleção de voz (narrated-video)
```

Ainda fora desta fatia (follow-ups): personagens extras, templates de história,
i18n do estúdio mobile, galeria rica de páginas.

## Typecheck

```bash
npm run typecheck
```

## Publicar (EAS / lojas)

Builds e submit via Expo Application Services: ver **[PUBLISH.md](./PUBLISH.md)**
(`eas.json`, perfis `preview` / `production`, checklist de segredos).

```bash
# após eas login + eas init (uma vez)
npm run eas:build:preview -- --platform android
```
