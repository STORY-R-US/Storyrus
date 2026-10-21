import { Link, useLocation } from "react-router-dom";
import logo from "./assets/logo.png";
import { staticPageMeta, usePageMeta } from "./pageMeta";
import { SiteBackNav } from "./SiteBackNav";
import "./landing.css";

const CONTACT = "info@storyrus.ai";
const UPDATED = "5 de outubro de 2026";

export function Legal({ kind }: { kind: "privacy" | "terms" }) {
  const privacy = kind === "privacy";
  const { pathname } = useLocation();
  usePageMeta(
    privacy
      ? staticPageMeta(pathname === "/privacy" ? "/privacy" : "/privacidade")
      : staticPageMeta(pathname === "/terms" ? "/terms" : "/termos"),
  );
  return (
    <div className="kid legal-page">
      <header className="knav">
        <Link to="/" className="kbrand"><img src={logo} alt="Story R Us" /></Link>
        <nav className="klinks">
          <Link to="/" className="kbtn kbtn-go">Início</Link>
        </nav>
      </header>
      <main className="ksection" style={{ maxWidth: 720, margin: "0 auto", textAlign: "left" }}>
        <SiteBackNav />
        <h1 className="ktitle">{privacy ? "Política De Privacidade" : "Termos De Uso"}</h1>
        <p className="ksub" style={{ textAlign: "left" }}>
          Última atualização: {UPDATED}.
        </p>
        {privacy ? (
          <>
            <p className="ksub" style={{ textAlign: "left" }}>
              A Story R Us (storyrus.ai) cria livros ilustrados personalizados a partir de uma foto
              que você envia. Esta política explica quais dados tratamos, para quê e como você pode
              exercer seus direitos — no Brasil (LGPD) e em outros países onde o serviço estiver
              disponível.
            </p>

            <h2>Quem somos</h2>
            <p>
              Controladora dos dados: Story R Us. Contato para privacidade e exclusão de dados:{" "}
              <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
            </p>

            <h2>O que coletamos</h2>
            <ul>
              <li>
                <strong>Conta:</strong> e-mail, senha (armazenada só como hash), data de cadastro e
                confirmação de e-mail.
              </li>
              <li>
                <strong>Perfil:</strong> nome completo, telefone, endereço (rua, número, complemento,
                bairro/distrito quando informado, cidade, estado/região e país) — usados para contato
                e, quando aplicável, entrega do livro impresso.
              </li>
              <li>
                <strong>Projeto:</strong> nome, idade e dedicatória da criança, foto enviada, estilo e
                tema escolhidos, e o conteúdo gerado (personagem, páginas, PDF, vídeo e, se você
                clonar, um sample de voz).
              </li>
              <li>
                <strong>Uso técnico:</strong> token de sessão no navegador, registros de acesso
                necessários à segurança e, quando o pagamento/frete estiver ativo, dados do pedido.
              </li>
            </ul>

            <h2>Para que usamos</h2>
            <p>
              Criar e entregar o livro e os vídeos do seu projeto; autenticar a conta; enviar e-mails
              transacionais (confirmação, redefinição de senha); processar pedidos de impressão quando
              você solicitar; melhorar estabilidade e segurança do serviço. Não vendemos dados
              pessoais e não usamos a foto do cliente para divulgação ou marketing.
            </p>

            <h2>Base e finalidade</h2>
            <p>
              Tratamos os dados para executar o contrato de prestação do serviço (criar o livro),
              cumprir obrigações legais quando houver, e, quando necessário, com base no seu
              consentimento (por exemplo, ao aceitar estes documentos no cadastro e ao enviar a foto
              da criança como responsável legal).
            </p>

            <h2>Compartilhamento com fornecedores</h2>
            <p>
              Podemos usar processadores para hospedagem, armazenamento de arquivos, envio de e-mail,
              modelos de IA (texto, imagem, vídeo ou voz), pagamento e frete. Eles recebem apenas o
              necessário para a tarefa e atuam sob instruções nossas. O frete de livros impressos, quando
              disponível, usa parceiros de logística — hoje com foco em entregas no Brasil.
            </p>

            <h2>Usuários internacionais</h2>
            <p>
              Você pode criar conta e informar endereço fora do Brasil. O ebook e os vídeos digitais
              estão disponíveis independentemente do país. A impressão física e o frete podem estar
              limitados a territórios atendidos pelos nossos parceiros; nesses casos o estúdio
              avisará antes da cobrança.
            </p>

            <h2>Exemplos Da Página Inicial</h2>
            <p>
              As fotos e vídeos de demonstração no site são materiais da plataforma, separados do que
              você envia no estúdio. A página <Link to="/exemplos">exemplos</Link> explica isso e
              aponta a vitrine da página inicial.
            </p>

            <h2>Conta e sessão</h2>
            <p>
              Sem cadastro, o navegador pode receber um token de convidado isolado. Com conta, o login
              exige e-mail verificado. Cada visitante vê só os próprios projetos.
            </p>

            <h2>Retenção e exclusão</h2>
            <p>
              Os arquivos ficam no armazenamento do projeto enquanto a conta existir. Para corrigir
              dados do perfil, use a conta ou escreva para {CONTACT}. Para apagar a conta e os
              arquivos associados, solicite pelo mesmo e-mail — responderemos em prazo razoável.
            </p>

            <h2>Seus direitos</h2>
            <p>
              Você pode solicitar acesso, correção, portabilidade, anonimização ou exclusão dos dados
              pessoais, além de informações sobre compartilhamentos. No Brasil, esses direitos seguem a
              LGPD. Escreva para {CONTACT}.
            </p>

            <h2>Crianças</h2>
            <p>
              O envio da foto deve ser feito pelo responsável legal, que autoriza o uso apenas para
              criar este livro personalizado. Não coletamos dados de crianças para marketing.
            </p>

            <h2>Alterações</h2>
            <p>
              Podemos atualizar esta política. A data no topo desta página indica a versão vigente.
              Mudanças relevantes podem ser comunicadas no site ou por e-mail.
            </p>

            <h2>Contato</h2>
            <p>
              Dúvidas sobre privacidade: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
            </p>
          </>
        ) : (
          <>
            <p className="ksub" style={{ textAlign: "left" }}>
              Ao criar conta ou usar storyrus.ai você concorda com estes Termos de uso. Se não
              concordar, não utilize o serviço.
            </p>

            <h2>O serviço</h2>
            <p>
              A Story R Us gera histórias e ilustrações com inteligência artificial a partir dos dados
              e da foto que você envia. O resultado pode variar. Você revisa a prévia antes de baixar o
              PDF ou pedir o livro impresso.
            </p>

            <h2>Cadastro e conta</h2>
            <p>
              Para usar o estúdio completo é necessário cadastrar-se com dados verdadeiros, aceitar
              estes Termos e a Política de privacidade, e confirmar o e-mail. Você é responsável por
              manter a senha em sigilo e pelas atividades na sua conta.
            </p>

            <h2>Responsável legal</h2>
            <p>
              Só envie foto de criança se você for o responsável legal e autorizar o uso exclusivo
              para criar este livro personalizado.
            </p>

            <h2>Pagamento do livro impresso</h2>
            <p>
              Gerar a história e as imagens entra no pedido. O que se fatura é o livro impresso,
              na ordem de serviço, conforme tamanho, acabamento, quantidade e frete. O parcelamento
              no cartão depende do gateway de pagamento estar ativo; até lá, o pedido de impresso
              pode seguir como cotação.
            </p>

            <h2>Impressão e envio</h2>
            <p>
              Quando a impressão estiver disponível, o endereço de entrega deve estar completo e
              válido. Entregas físicas podem estar restritas a países ou regiões atendidos pelos
              parceiros logísticos (com prioridade atual ao Brasil). Fora dessas áreas, o conteúdo
              livro digital (PDF) continua disponível no pedido.
            </p>

            <h2>Usuários internacionais</h2>
            <p>
              Contas e endereços fora do Brasil são aceitos no cadastro. Idiomas e formatos do livro
              seguem as opções do estúdio. Regras fiscais, impostos de importação ou restrições
              locais de envio, quando houver impressão internacional, são de responsabilidade do
              destinatário conforme a legislação aplicável.
            </p>

            <h2>Propriedade e uso</h2>
            <p>
              Você pode usar o livro gerado para uso pessoal e familiar. Não redistribua o software,
              não explore falhas da API e não use o serviço para conteúdo ilegal, abusivo ou que
              viole direitos de terceiros.
            </p>

            <h2>Limitação</h2>
            <p>
              O serviço é oferecido “como está”. Na medida permitida pela lei, não garantimos
              disponibilidade ininterrupta nem resultado artístico específico. Em caso de falha
              imputável a nós, a responsabilidade limita-se, em regra, a refazer o livro ou o pedido
              afetado.
            </p>

            <h2>Alterações e vigência</h2>
            <p>
              Podemos atualizar estes termos. A data no topo indica a versão vigente. O uso
              continuado após a publicação das alterações constitui aceite, salvo quando a lei exigir
              novo consentimento.
            </p>

            <h2>Contato</h2>
            <p>
              <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
            </p>
          </>
        )}
        <p style={{ marginTop: 28 }}>
          <Link to="/" className="kbtn kbtn-primary">
            Voltar à página inicial
          </Link>
        </p>
      </main>
    </div>
  );
}
