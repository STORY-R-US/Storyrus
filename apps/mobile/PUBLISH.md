# Publicar o app mobile (EAS)

Pipeline de build e envio às lojas com **Expo Application Services (EAS)**.
Os segredos (Apple / Google / Expo token) **não** ficam no repositório — só no
[Expo dashboard](https://expo.dev) e no CI quando houver.

Pré-requisito local: Node 20+, conta Expo, e o app em `apps/mobile`.

## 1) Uma vez — projeto EAS

```bash
cd apps/mobile
npm ci
npx eas-cli@latest login          # conta Expo
npx eas-cli@latest init           # cria projeto e grava projectId em app.json
```

`eas init` adiciona `expo.extra.eas.projectId` em `app.json`. Committe esse
diff quando o projeto existir de verdade. Até lá, `eas.json` + este doc bastam
para o time saber o caminho.

IDs de store já definidos em `app.json`:

| Plataforma | Campo | Valor |
|------------|--------|--------|
| iOS | `ios.bundleIdentifier` | `ai.storyrus.app` |
| Android | `android.package` | `ai.storyrus.app` |

Troque só se o domínio/org for outro — mantenha iOS e Android alinhados.

## 2) Perfis (`eas.json`)

| Perfil | Uso | Artefato típico |
|--------|-----|-----------------|
| `development` | Dev client + simulador iOS / APK Android | interno |
| `preview` | QA / TestFlight interno / APK | interno |
| `production` | Lojas (AAB Android + IPA iOS); `autoIncrement` remoto | store |

Todos os perfis injetam `EXPO_PUBLIC_API_BASE=https://storyrus.ai` (BFF same-origin
com proxy `/v1`). Para builds apontando a outro ambiente, sobrescreva no perfil
ou passe `--env` no CLI — não committe URLs de staging com segredos.

## 3) Build

```bash
cd apps/mobile

# QA interno (APK / internal distribution)
npx eas-cli@latest build --profile preview --platform android
npx eas-cli@latest build --profile preview --platform ios

# Store
npx eas-cli@latest build --profile production --platform all
```

Sem credenciais de signing ainda, o EAS guia a criação (keystore Android /
certificados iOS). Aceite o fluxo gerenciado pelo Expo até ter um processo
próprio.

## 4) Submit (lojas)

Configure no **Expo dashboard** (ou via `eas credentials`):

- **Google Play** — service account JSON com acesso à Play Console; app criado
  com package `ai.storyrus.app`.
- **App Store Connect** — Apple Team, app com bundle `ai.storyrus.app`, e
  `submit.production.ios.ascAppId` em `eas.json` (substitua o placeholder).

```bash
npx eas-cli@latest submit --profile production --platform android
npx eas-cli@latest submit --profile production --platform ios
```

O perfil `production` no submit Android usa track `internal` + `draft` de
propósito — promove manualmente na Play Console até o fluxo estar estável.

## 5) Segredos / CI (quando existir)

Não versionar:

| Segredo | Onde |
|---------|------|
| `EXPO_TOKEN` | GitHub Actions / Expo CI |
| Google Play service account JSON | Expo credentials ou secret do CI |
| Apple App Store Connect API key | Expo credentials |

Sugestão futura de workflow (não incluso neste PR): job manual
`workflow_dispatch` que rode `eas build --non-interactive` com `EXPO_TOKEN`.
O CI atual só faz `npm ci` + `typecheck` em `apps/mobile`.

## 6) Checklist antes do primeiro store build

- [ ] `eas init` commitado (`projectId` em `app.json`)
- [ ] Ícones / splash / screenshots das lojas
- [ ] Privacy policy / termos (já no web) linkados na ficha da loja
- [ ] API de produção estável em `https://storyrus.ai`
- [ ] Conta Apple Developer + Google Play Console ativas
- [ ] `ascAppId` real em `eas.json` (iOS submit)

## Relacionado

- Dev local / `EXPO_PUBLIC_API_BASE`: `apps/mobile/README.md`
- Deploy web + API: `DEPLOY.md` (raiz)
- Issue: STO-34
