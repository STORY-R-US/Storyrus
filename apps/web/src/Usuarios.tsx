import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import logo from "./assets/logo.png";
import { api, getToken } from "./api";
import { OwnerAccessGate } from "./OwnerAccessGate";
import { OwnerNav } from "./OwnerNav";
import {
  OWNER_SESSION_TOKEN,
  apiOwnerPassword,
  canTryOwnerSession,
  clearOwnerSecret,
  isOwnerAuthFailure,
  isOwnerTransientFailure,
  ownerGateError,
  persistOwnerSecret,
  readOwnerSecret,
} from "./ownerSession";
import { useOwnerPageTitle } from "./useOwnerPageTitle";
import type { OwnerUser } from "./types";
import "./usage.css";


function when(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function matches(user: OwnerUser, query: string): boolean {
  const hay = [user.full_name, user.email, user.phone, user.city]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(query.trim().toLowerCase());
}

const EMPTY: OwnerUser = {
  id: "",
  email: "",
  credits: 0,
  created_at: "",
  project_count: 0,
  full_name: "",
  phone: "",
  email_verified: false,
  postal_code: "",
  street: "",
  number: "",
  complement: "",
  district: "",
  city: "",
  state: "",
  country: "",
};

export function Usuarios() {
  useOwnerPageTitle("/usuarios");
  const [password, setPassword] = useState(() => readOwnerSecret());
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<OwnerUser[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OwnerUser | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sessionTried, setSessionTried] = useState(false);
  const [lastStatus, setLastStatus] = useState<number | undefined>();
  const autoRetryUsed = useRef(false);

  const visible = useMemo(
    () => (users ?? []).filter((user) => (query.trim() ? matches(user, query) : true)),
    [users, query],
  );

  const ownerSecret = apiOwnerPassword(password);

  const load = useCallback(async (secret: string) => {
    setLoading(true);
    setError(null);
    setLastStatus(undefined);
    try {
      const report = await api.users(apiOwnerPassword(secret));
      setUsers(report.users);
      setTotal(report.total);
      const next = apiOwnerPassword(secret) ? secret.trim() : OWNER_SESSION_TOKEN;
      persistOwnerSecret(next);
      setPassword(next);
      autoRetryUsed.current = false;
    } catch (err) {
      const status = (err as Error & { status?: number }).status;
      const raw = err instanceof Error ? err.message : "Falha ao carregar usuários.";
      setLastStatus(status);
      if (isOwnerAuthFailure(status)) {
        clearOwnerSecret();
        setPassword("");
        setUsers(null);
        setDetail(null);
        setSelectedId(null);
      }
      setError(
        ownerGateError(status, raw, {
          usedSession: !apiOwnerPassword(secret) && Boolean(getToken()),
        }),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (password) {
      void load(password);
      return;
    }
    if (!sessionTried && canTryOwnerSession()) {
      setSessionTried(true);
      void load(OWNER_SESSION_TOKEN);
    }
  }, [password, load, sessionTried]);

  useEffect(() => {
    if (users !== null || loading || !error || autoRetryUsed.current) return;
    if (!isOwnerTransientFailure(lastStatus, error)) return;
    if (!canTryOwnerSession() && !password) return;
    autoRetryUsed.current = true;
    const id = window.setTimeout(() => {
      void load(password || OWNER_SESSION_TOKEN);
    }, 3500);
    return () => window.clearTimeout(id);
  }, [users, loading, error, lastStatus, password, load]);

  function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    const next = draft.trim();
    if (next) void load(next);
  }

  async function openUser(id: string) {
    const fromList = users?.find((item) => item.id === id) ?? null;
    setSelectedId(id);
    setSaved(false);
    setConfirmDelete(false);
    setError(null);
    if (fromList) setDetail(fromList);
    try {
      setDetail(await api.user(ownerSecret, id));
    } catch (err) {
      if (!fromList) {
        setError(err instanceof Error ? err.message : "Falha ao abrir o usuário.");
      }
    }
  }

  function setField<K extends keyof OwnerUser>(key: K, value: OwnerUser[K]) {
    setDetail((prev) => (prev ? { ...prev, [key]: value } : prev));
    setSaved(false);
  }

  async function saveUser(ev: FormEvent) {
    ev.preventDefault();
    if (!detail) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const next = await api.updateUser(ownerSecret, detail.id, {
        email: detail.email.trim(),
        email_verified: Boolean(detail.email_verified),
        full_name: (detail.full_name ?? "").trim() || null,
        phone: (detail.phone ?? "").trim() || null,
        postal_code: (detail.postal_code ?? "").trim() || null,
        street: (detail.street ?? "").trim() || null,
        number: (detail.number ?? "").trim() || null,
        complement: (detail.complement ?? "").trim() || null,
        district: (detail.district ?? "").trim() || null,
        city: (detail.city ?? "").trim() || null,
        state: (detail.state ?? "").trim() || null,
        country: (detail.country ?? "").trim().toUpperCase() || null,
      });
      setDetail(next);
      setUsers((list) => list?.map((item) => (item.id === next.id ? { ...item, ...next } : item)) ?? null);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar o usuário.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteUser() {
    if (!detail) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteUser(ownerSecret, detail.id);
      setUsers((list) => list?.filter((item) => item.id !== detail.id) ?? null);
      setTotal((n) => Math.max(0, n - 1));
      setSelectedId(null);
      setDetail(null);
      setConfirmDelete(false);
      setSaved(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir o usuário.");
    } finally {
      setDeleting(false);
    }
  }

  const unlocked = users !== null;
  const transient = Boolean(error && isOwnerTransientFailure(lastStatus, error));
  const opening =
    !unlocked &&
    (loading ||
      Boolean(password) ||
      (!sessionTried && canTryOwnerSession()) ||
      (transient && canTryOwnerSession()));

  if (!unlocked) {
    return (
      <OwnerAccessGate
        title="Usuários"
        loginNext="/usuarios"
        draft={draft}
        onDraftChange={setDraft}
        onSubmitPassword={onSubmit}
        onRetrySession={() => void load(password || OWNER_SESSION_TOKEN)}
        loading={loading || (!sessionTried && canTryOwnerSession() && !error)}
        error={error}
        opening={opening && !isOwnerAuthFailure(lastStatus)}
        transient={transient}
      />
    );
  }

  const form = detail ?? EMPTY;

  return (
    <div className="usage usage-wide">
      <header className="usage-head">
        <img className="hdr-logo" src={logo} alt="Story R Us" />
        <div>
          <h1>Usuários</h1>
          <p className="muted">
            Contas cadastradas (sem convidados). {total} no total. Clique numa conta para ver, editar
            ou excluir.
          </p>
        </div>
        <OwnerNav current="usuarios" />
        <button
          className="link"
          type="button"
          onClick={() => {
            clearOwnerSecret();
            setPassword("");
            setUsers(null);
            setDetail(null);
            setSelectedId(null);
            setDraft("");
            setQuery("");
            setSessionTried(true);
          }}
        >
          Sair
        </button>
      </header>

      {error && <p className="error">{error}</p>}

      {(users ?? []).length === 0 ? (
        <p className="muted">Nenhuma conta cadastrada ainda.</p>
      ) : (
        <div className="usage-user-layout">
          <section className="usage-panel usage-user-list-pane">
            <label className="usage-user-search">
              Buscar
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Nome, e-mail, telefone ou cidade"
                data-testid="owner-user-search"
              />
            </label>
            {visible.length === 0 ? (
              <p className="muted">Nenhuma conta com esse filtro.</p>
            ) : (
              <ul className="usage-user-list" aria-label="Lista de usuários">
                {visible.map((user) => (
                  <li key={user.id}>
                    <button
                      type="button"
                      className={`usage-user-card${selectedId === user.id ? " is-on" : ""}`}
                      aria-pressed={selectedId === user.id}
                      onClick={() => void openUser(user.id)}
                      data-testid={`owner-user-open-${user.id}`}
                    >
                      <div className="usage-user-card-top">
                        <div>
                          <strong>{user.full_name || "Sem nome"}</strong>
                          <p className="usage-user-email">{user.email}</p>
                        </div>
                        <span
                          className={`usage-badge${user.email_verified ? " is-ok" : ""}`}
                        >
                          {user.email_verified ? "Verificado" : "Não verificado"}
                        </span>
                      </div>
                      <p className="usage-user-meta">
                        <span>{user.phone || "Sem telefone"}</span>
                        <span>
                          {user.project_count} projeto{user.project_count === 1 ? "" : "s"}
                        </span>
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {selectedId && detail ? (
            <section className="usage-panel usage-user-detail" data-testid="owner-user-detail">
              <form onSubmit={(ev) => void saveUser(ev)}>
                <h2>Dados da conta</h2>
                <p className="muted">
                  Cadastro {when(detail.created_at)} · {detail.project_count} projeto
                  {detail.project_count === 1 ? "" : "s"}
                  {detail.terms_accepted_at ? ` · termos em ${when(detail.terms_accepted_at)}` : ""}
                </p>
                <div className="usage-user-form">
                  <p className="usage-user-section usage-span-2">Contato</p>
                  <label>
                    Nome
                    <input
                      value={form.full_name ?? ""}
                      onChange={(e) => setField("full_name", e.target.value)}
                      data-testid="owner-user-full-name"
                    />
                  </label>
                  <label>
                    E-mail
                    <input
                      type="email"
                      required
                      value={form.email}
                      onChange={(e) => setField("email", e.target.value)}
                      data-testid="owner-user-email"
                    />
                  </label>
                  <label>
                    Telefone
                    <input
                      value={form.phone ?? ""}
                      onChange={(e) => setField("phone", e.target.value)}
                      data-testid="owner-user-phone"
                    />
                  </label>
                  <label className="usage-check">
                    <input
                      type="checkbox"
                      checked={Boolean(form.email_verified)}
                      onChange={(e) => setField("email_verified", e.target.checked)}
                      data-testid="owner-user-verified"
                    />
                    E-mail verificado
                  </label>
                  <p className="usage-user-section usage-span-2">Endereço</p>
                  <label>
                    CEP / ZIP
                    <input
                      value={form.postal_code ?? ""}
                      onChange={(e) => setField("postal_code", e.target.value)}
                      data-testid="owner-user-postal"
                    />
                  </label>
                  <label className="usage-span-2">
                    Rua
                    <input
                      value={form.street ?? ""}
                      onChange={(e) => setField("street", e.target.value)}
                      data-testid="owner-user-street"
                    />
                  </label>
                  <label>
                    Número
                    <input
                      value={form.number ?? ""}
                      onChange={(e) => setField("number", e.target.value)}
                    />
                  </label>
                  <label>
                    Complemento
                    <input
                      value={form.complement ?? ""}
                      onChange={(e) => setField("complement", e.target.value)}
                    />
                  </label>
                  <label>
                    Bairro
                    <input
                      value={form.district ?? ""}
                      onChange={(e) => setField("district", e.target.value)}
                    />
                  </label>
                  <label>
                    Cidade
                    <input
                      value={form.city ?? ""}
                      onChange={(e) => setField("city", e.target.value)}
                      data-testid="owner-user-city"
                    />
                  </label>
                  <label>
                    Estado
                    <input
                      value={form.state ?? ""}
                      onChange={(e) => setField("state", e.target.value)}
                    />
                  </label>
                  <label>
                    País
                    <input
                      maxLength={2}
                      value={form.country ?? ""}
                      onChange={(e) => setField("country", e.target.value.toUpperCase())}
                    />
                  </label>
                </div>
                <div className="usage-user-actions">
                  <button type="submit" disabled={saving || deleting} data-testid="owner-user-save">
                    {saving ? "Salvando…" : "Salvar"}
                  </button>
                  <button
                    type="button"
                    className="link"
                    onClick={() => {
                      setSelectedId(null);
                      setDetail(null);
                      setSaved(false);
                      setConfirmDelete(false);
                    }}
                  >
                    Fechar
                  </button>
                  {saved && (
                    <span className="muted" data-testid="owner-user-saved">
                      Alterações salvas.
                    </span>
                  )}
                </div>
                <div className="usage-user-danger">
                  {confirmDelete ? (
                    <>
                      <p className="error">
                        Apaga a conta {detail.email} e os projetos dela. Isso não volta atrás.
                      </p>
                      <button
                        type="button"
                        className="usage-btn-danger"
                        disabled={deleting}
                        onClick={() => void deleteUser()}
                        data-testid="owner-user-delete-confirm"
                      >
                        {deleting ? "Excluindo…" : "Confirmar exclusão"}
                      </button>
                      <button
                        type="button"
                        className="link"
                        disabled={deleting}
                        onClick={() => setConfirmDelete(false)}
                      >
                        Cancelar
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="usage-btn-danger"
                      onClick={() => setConfirmDelete(true)}
                      data-testid="owner-user-delete"
                    >
                      Excluir usuário
                    </button>
                  )}
                </div>
              </form>
            </section>
          ) : (
            <section
              className="usage-panel usage-user-detail usage-user-empty"
              data-testid="owner-user-placeholder"
            >
              <h2>Dados da conta</h2>
              <p className="muted">Clique numa conta na lista para ver e editar os dados.</p>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
