import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Exemplos } from "./Exemplos";
import { Legal } from "./Legal";
import { NotFound } from "./NotFound";
import { BackendStatus } from "./BackendStatus";

const Landing = lazy(() =>
  import("./Landing").then((m) => ({ default: m.Landing })),
);
const CatalogPage = lazy(() =>
  import("./CatalogPages").then((m) => ({ default: m.CatalogPage })),
);
const CategoryCatalogPage = lazy(() =>
  import("./CatalogPages").then((m) => ({ default: m.CategoryCatalogPage })),
);
const BookPage = lazy(() =>
  import("./CatalogPages").then((m) => ({ default: m.BookPage })),
);
const App = lazy(() => import("./App").then((m) => ({ default: m.App })));
const Auth = lazy(() => import("./Auth").then((m) => ({ default: m.Auth })));
const VerifyEmail = lazy(() =>
  import("./VerifyEmail").then((m) => ({ default: m.VerifyEmail })),
);
const ForgotPassword = lazy(() =>
  import("./ForgotPassword").then((m) => ({ default: m.ForgotPassword })),
);
const ResetPassword = lazy(() =>
  import("./ResetPassword").then((m) => ({ default: m.ResetPassword })),
);
const Usage = lazy(() =>
  import("./Usage").then((m) => ({ default: m.Usage })),
);
const Pedidos = lazy(() =>
  import("./Pedidos").then((m) => ({ default: m.Pedidos })),
);
const Usuarios = lazy(() =>
  import("./Usuarios").then((m) => ({ default: m.Usuarios })),
);
const Conta = lazy(() =>
  import("./Conta").then((m) => ({ default: m.Conta })),
);

/**
 * Roteamento do site:
 *   /              → Landing
 *   /cartoon       → Landing (mesma página, fotos em desenho)
 *   /catalogo      → Catálogo completo
 *   /catalogo/:categoria → Catálogo de uma categoria
 *   /livro/:indice → Página do livro
 *   /entrar        → Login
 *   /cadastro      → Criar conta
 *   /verificar-email → Confirmação de e-mail (token)
 *   /esqueci-senha → Pedir link de redefinição
 *   /redefinir-senha → Nova senha (token)
 *   /app           → Estúdio (conta obrigatória)
 *   /conta         → Perfil do usuário (editar dados)
 *   /gastos        → Painel privado de custos USD
 *   /pedidos       → Painel privado de pedidos
 *   /usuarios      → Painel privado de contas cadastradas
 *   /landing       → Landing (compatibilidade)
 *   /privacidade   → Política de privacidade
 *   /termos        → Termos de uso
 *   /exemplos      → Demonstrações da plataforma (citadas na privacidade)
 *   *              → 404
 *
 * Landing / Studio (via App) / Usage are lazy-loaded into separate chunks.
 * Suspense fallback is null so the landing visual stays unchanged.
 */
export function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/cartoon" element={<Landing variant="cartoon" />} />
        <Route path="/catalogo" element={<CatalogPage />} />
        <Route path="/catalogo/:categoria" element={<CategoryCatalogPage />} />
        <Route path="/livro/:indice" element={<BookPage />} />
        <Route path="/entrar" element={<Auth mode="login" />} />
        <Route path="/cadastro" element={<Auth mode="signup" />} />
        <Route path="/verificar-email" element={<VerifyEmail />} />
        <Route path="/esqueci-senha" element={<ForgotPassword />} />
        <Route path="/redefinir-senha" element={<ResetPassword />} />
        <Route path="/app" element={<App />} />
        <Route path="/conta" element={<Conta />} />
        <Route path="/gastos" element={<Usage />} />
        <Route path="/pedidos" element={<Pedidos />} />
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="/landing" element={<Landing />} />
        <Route path="/privacidade" element={<Legal kind="privacy" />} />
        <Route path="/privacy" element={<Legal kind="privacy" />} />
        <Route path="/termos" element={<Legal kind="terms" />} />
        <Route path="/terms" element={<Legal kind="terms" />} />
        <Route path="/exemplos" element={<Exemplos />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

export function Root() {
  return (
    <BrowserRouter>
      <BackendStatus />
      <AppRoutes />
    </BrowserRouter>
  );
}
