import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { formatCep, useCepLookup } from "../cepLookup";
import type { PrintAddress, PrintOrder } from "../types";
import { useStudioI18n } from "./useStudioI18n";

type QtyMode = "one" | "copies" | "package";

function modeFor(quantity: number): QtyMode {
  if (quantity >= 11) return "package";
  if (quantity >= 2) return "copies";
  return "one";
}

function countFor(mode: QtyMode, copies: string, pack: string): number {
  if (mode === "one") return 1;
  const raw = Number(mode === "copies" ? copies : pack);
  const n = Math.floor(raw);
  if (mode === "copies") return Math.max(2, Math.min(10, Number.isNaN(n) ? 2 : n));
  return Math.max(11, Math.min(500, Number.isNaN(n) ? 11 : n));
}

function money(cents: number | null): string {
  if (cents == null) return "—";
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const emptyAddress: PrintAddress = {
  recipient_name: "",
  postal_code: "",
  street: "",
  number: "",
  complement: "",
  district: "",
  city: "",
  state: "",
};

/** Endereço, frete e pagamento do impresso. O gateway só abre quando estiver configurado. */
export function PrintCheckout({ projectId }: { projectId: string }) {
  const { t } = useStudioI18n();
  const [order, setOrder] = useState<PrintOrder | null>(null);
  const [address, setAddress] = useState<PrintAddress>(emptyAddress);
  const [installments, setInstallments] = useState(1);
  const [note, setNote] = useState<string | null>(null);
  const [mode, setMode] = useState<QtyMode>("one");
  const [copies, setCopies] = useState("2");
  const [pack, setPack] = useState("11");
  const cepStatus = useCepLookup(address.postal_code, true, (addr) => {
    setAddress((prev) => ({
      ...prev,
      postal_code: addr.postal_code,
      street: addr.street || prev.street,
      district: addr.district || prev.district,
      city: addr.city || prev.city,
      state: addr.state || prev.state,
    }));
  });

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [next, me] = await Promise.all([
          api.printOrder(projectId),
          api.me().catch(() => null),
        ]);
        if (cancel) return;
        setOrder(next);
        const qty = next.quantity || 1;
        setMode(modeFor(qty));
        if (qty >= 2 && qty <= 10) setCopies(String(qty));
        if (qty >= 11) setPack(String(qty));
        const fromOrder = Boolean(next.postal_code || next.street);
        setAddress({
          recipient_name:
            next.recipient_name ||
            (!fromOrder ? me?.full_name || "" : "") ||
            "",
          postal_code: next.postal_code || (!fromOrder ? me?.postal_code || "" : "") || "",
          street: next.street || (!fromOrder ? me?.street || "" : "") || "",
          number: next.number || (!fromOrder ? me?.number || "" : "") || "",
          complement: next.complement || (!fromOrder ? me?.complement || "" : "") || "",
          district: next.district || (!fromOrder ? me?.district || "" : "") || "",
          city: next.city || (!fromOrder ? me?.city || "" : "") || "",
          state: next.state || (!fromOrder ? me?.state || "" : "") || "",
        });
      } catch (err) {
        if (!cancel) setNote(err instanceof Error ? err.message : "Erro ao carregar pedido.");
      }
    })();
    return () => {
      cancel = true;
    };
  }, [projectId]);

  const quantityLocked = order?.payment_status === "paid" || order?.payment_status === "pending";

  async function applyQuantity(nextMode: QtyMode, nextCopies = copies, nextPack = pack) {
    const quantity = countFor(nextMode, nextCopies, nextPack);
    setMode(nextMode);
    setNote(null);
    try {
      setOrder(await api.setPrintQuantity(projectId, quantity));
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Não foi possível salvar a quantidade.");
    }
  }

  async function saveAddress(ev: FormEvent) {
    ev.preventDefault();
    setNote(null);
    try {
      setOrder(await api.savePrintAddress(projectId, address));
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Endereço inválido.");
    }
  }

  async function quote() {
    setNote(null);
    try {
      setOrder(await api.quotePrintFreight(projectId));
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Frete indisponível.");
    }
  }

  async function choose(serviceId: number) {
    setNote(null);
    try {
      setOrder(await api.selectPrintFreight(projectId, serviceId));
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Não foi possível escolher o frete.");
    }
  }

  async function pay() {
    setNote(null);
    try {
      const next = await api.checkoutPrint(projectId, installments);
      setOrder(next);
      if (next.checkout_url) window.location.assign(next.checkout_url);
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Pagamento indisponível.");
    }
  }

  if (!order) return note ? <p className="muted">{note}</p> : null;

  return (
    <div style={{ marginTop: 12 }}>
      <p className="muted">
        {order.code}
        {order.book_price_cents != null
          ? ` · Livro ${money(order.book_price_cents)} × ${order.quantity} = ${money(order.book_price_cents * order.quantity)}`
          : ""}
        {order.block_reason ? ` · ${order.block_reason}` : ""}
      </p>
      <div className="studio-choice print-quantity" role="group" aria-label={t.quantity}>
        <span className="studio-choice-label">{t.quantity}</span>
        <div className="studio-actions">
          {(["one", "copies", "package"] as const).map((choice) => (
            <button
              key={choice}
              type="button"
              className={mode === choice ? "studio-pick is-on" : "studio-pick"}
              aria-pressed={mode === choice}
              disabled={quantityLocked}
              onClick={() => void applyQuantity(choice)}
            >
              {choice === "one" ? t.quantityOne : choice === "copies" ? t.quantityCopies : t.quantityPackage}
            </button>
          ))}
        </div>
        {mode === "copies" && (
          <label className="studio-field">
            {t.quantityCopies}
            <input
              type="number"
              inputMode="numeric"
              min={2}
              max={10}
              disabled={quantityLocked}
              value={copies}
              data-testid="print-quantity-copies"
              onChange={(e) => {
                const value = e.target.value;
                setCopies(value);
                const n = Number(value);
                if (value !== "" && n >= 2 && n <= 10) void applyQuantity("copies", value, pack);
              }}
            />
          </label>
        )}
        {mode === "copies" && <p className="muted field-hint">{t.quantityCopiesHint}</p>}
        {mode === "package" && (
          <label className="studio-field">
            {t.quantityPackage}
            <input
              type="number"
              inputMode="numeric"
              min={11}
              max={500}
              disabled={quantityLocked}
              value={pack}
              data-testid="print-quantity-package"
              onChange={(e) => {
                const value = e.target.value;
                setPack(value);
                const n = Number(value);
                if (value !== "" && n >= 11 && n <= 500) void applyQuantity("package", copies, value);
              }}
            />
          </label>
        )}
        {mode === "package" && <p className="muted field-hint">{t.quantityPackageHint}</p>}
      </div>
      {order.tracking_code && <p role="status">Rastreio {order.tracking_code}</p>}
      <form onSubmit={(ev) => void saveAddress(ev)} style={{ display: "grid", gap: 8, marginTop: 8 }}>
        <label>
          Nome
          <input
            value={address.recipient_name}
            onChange={(e) => setAddress({ ...address, recipient_name: e.target.value })}
          />
        </label>
        <label>
          CEP
          <input
            value={address.postal_code}
            inputMode="numeric"
            maxLength={9}
            autoComplete="postal-code"
            onChange={(e) => setAddress({ ...address, postal_code: formatCep(e.target.value) })}
          />
          {cepStatus === "loading" && <small>Buscando endereço…</small>}
          {cepStatus === "ok" && <small>Endereço preenchido. Confira e informe o número.</small>}
          {cepStatus === "miss" && <small>CEP não encontrado. Preencha o endereço.</small>}
          {cepStatus === "error" && (
            <small>Não foi possível buscar o CEP. Preencha o endereço.</small>
          )}
        </label>
        <label>
          Rua
          <input value={address.street} onChange={(e) => setAddress({ ...address, street: e.target.value })} />
        </label>
        <label>
          Número
          <input value={address.number} onChange={(e) => setAddress({ ...address, number: e.target.value })} />
        </label>
        <label>
          Bairro
          <input
            value={address.district}
            onChange={(e) => setAddress({ ...address, district: e.target.value })}
          />
        </label>
        <label>
          Cidade
          <input value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} />
        </label>
        <label>
          UF
          <input
            value={address.state}
            maxLength={2}
            onChange={(e) => setAddress({ ...address, state: e.target.value })}
          />
        </label>
        <button type="submit">Salvar endereço</button>
      </form>
      <button type="button" style={{ marginTop: 8 }} onClick={() => void quote()}>
        Calcular frete
      </button>
      {(order.freight_options ?? []).length > 0 && (
        <ul>
          {order.freight_options.map((item) => (
            <li key={item.service_id}>
              <button type="button" onClick={() => void choose(item.service_id)}>
                {item.service_name} · {money(item.price_cents)}
                {item.delivery_days == null ? " · prazo não informado" : ` · ${item.delivery_days} dias`}
              </button>
            </li>
          ))}
        </ul>
      )}
      <label style={{ display: "block", marginTop: 8 }}>
        Parcelas
        <select value={installments} onChange={(e) => setInstallments(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
            <option key={n} value={n}>
              {n}x
            </option>
          ))}
        </select>
      </label>
      <button type="button" disabled={!order.checkout_available} onClick={() => void pay()}>
        Pagar impresso
      </button>
      {!order.checkout_available && (
        <p className="muted">O gateway de pagamento ainda não foi escolhido. O pedido segue como cotação.</p>
      )}
      {note && <p className="muted">{note}</p>}
    </div>
  );
}
