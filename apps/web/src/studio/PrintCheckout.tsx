import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { formatCep, useCepLookup, type CepStatus } from "../cepLookup";
import type { PrintAddress, PrintOrder, Project, PurchaseChoice } from "../types";
import { useStudioI18n } from "./useStudioI18n";
import { money, purchaseCopy } from "./purchaseCopy";

const CEP_STATUS: Record<string, Partial<Record<CepStatus, string>>> = {
  pt: { loading: "Buscando endereço…", ok: "Endereço preenchido. Confira e informe o número.", miss: "CEP não encontrado. Preencha o endereço.", error: "Não foi possível buscar o CEP. Preencha o endereço." },
  en: { loading: "Looking up address…", ok: "Address filled in. Check it and add the number.", miss: "CEP not found. Please fill in the address.", error: "Could not look up the CEP. Please fill in the address." },
  es: { loading: "Buscando dirección…", ok: "Dirección rellenada. Revisa e indica el número.", miss: "CEP no encontrado. Completa la dirección.", error: "No fue posible buscar el CEP. Completa la dirección." },
};

const empty: PrintAddress = {
  recipient_name: "",
  postal_code: "",
  street: "",
  number: "",
  complement: "",
  district: "",
  city: "",
  state: "",
};

export function PrintCheckout({
  projectId,
  onProject,
  canConfirmPayment = false,
}: {
  projectId: string;
  onProject?: (project: Project) => void;
  canConfirmPayment?: boolean;
}) {
  const { lang } = useStudioI18n();
  const t = purchaseCopy(lang);
  const [order, setOrder] = useState<PrintOrder | null>(null);
  const [address, setAddress] = useState<PrintAddress>(empty);
  const [savedAddress, setSavedAddress] = useState<PrintAddress>(empty);
  const [note, setNote] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [attempt, setAttempt] = useState(0);
  const [installments, setInstallments] = useState(1);
  const [quantity, setQuantity] = useState("1");
  const deliverySent =
    ["sent_for_validation", "approved"].includes(order?.status || "") ||
    Boolean(order?.tracking_code);
  const cepStatus = useCepLookup(
    address.postal_code,
    address.postal_code !== savedAddress.postal_code && !busy && !deliverySent,
    (a) =>
      setAddress((prev) => ({
        ...prev,
        postal_code: a.postal_code,
        street: a.street || prev.street,
        district: a.district || prev.district,
        city: a.city || prev.city,
        state: a.state || prev.state,
      })),
  );

  useEffect(() => {
    let cancel = false;
    setNote(null);
    void api
      .printOrder(projectId)
      .then((next) => {
        if (cancel) return;
        setOrder(next);
        setQuantity(String(next.quantity));
        const a = Object.fromEntries(
          Object.keys(empty).map((key) => [
            key,
            next[key as keyof PrintOrder] || "",
          ]),
        ) as unknown as PrintAddress;
        setAddress(a);
        setSavedAddress(a);
      })
      .catch((err: Error) => {
        if (!cancel) setNote(err.message);
      });
    return () => {
      cancel = true;
    };
  }, [projectId, attempt]);

  const refresh = useCallback(async () => {
    const [next, project] = await Promise.all([
      api.printOrder(projectId),
      api.getProject(projectId),
    ]);
    setOrder(next);
    onProject?.(project);
  }, [projectId, onProject]);
  useEffect(() => {
    if (order?.payment_status !== "pending") return;
    const id = window.setInterval(() => {
      void refresh().catch(() => {});
    }, 5000);
    return () => window.clearInterval(id);
  }, [order?.payment_status, refresh]);

  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setNote(null);
    setSaved(false);
    try {
      await action();
    } catch (err) {
      setNote((err as Error).message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  if (!order)
    return (
      <div role="status">
        {note || t.loading}
        {note && (
          <button type="button" onClick={() => setAttempt((n) => n + 1)}>
            {t.retry}
          </button>
        )}
      </div>
    );
  const specLocked = busy || ["pending", "paid"].includes(order.payment_status);
  const addressLocked = busy || deliverySent;
  const addressDirty = JSON.stringify(address) !== JSON.stringify(savedAddress);
  const digital = order.fulfillment === "digital";
  const choice: PurchaseChoice = {
    fulfillment: digital ? "digital" : "print",
    ebook: !!order.extra_ebook,
    video: !!order.extra_video,
  };
  const prices = order.prices;
  const books =
    order.book_price_cents == null
      ? null
      : order.book_price_cents * order.quantity;
  const total =
    order.items_price_cents != null ? order.items_price_cents : digital ? null : books;
  const extrasTotal = !digital && total != null && books != null ? total - books : 0;
  const ready = (digital || !addressDirty) && total != null;
  const quantityDirty = !digital && quantity !== String(order.quantity);
  const itemPrice = (item: "ebook" | "video" | "bundle") =>
    prices ? (digital ? prices.digital[item] : prices.extra[item]) : null;
  // No impresso os itens digitais somam ao livro ("+ R$ 29"); no só digital o valor é o preço cheio.
  const itemMoney = (cents: number | null) => `${digital ? "" : "+ "}${money(cents)}`;
  const itemsSum =
    itemPrice("ebook") != null && itemPrice("video") != null
      ? (itemPrice("ebook") as number) + (itemPrice("video") as number)
      : null;
  const extrasLabel =
    choice.ebook && choice.video ? t.bothItems : choice.video ? t.videoItem : t.ebookItem;
  function choose(next: PurchaseChoice) {
    void run(async () => setOrder(await api.setPrintPurchase(projectId, next)));
  }
  function saveAddress(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      setOrder(await api.savePrintAddress(projectId, address));
      setSavedAddress({ ...address });
    });
  }
  return (
    <section className="purchase-checkout" aria-label={t.summary}>
      <p className="purchase-order-code">
        <strong>{order.code}</strong>
      </p>
      <p className="muted">{digital ? t.includesDigital : t.includes}</p>
      <div className="purchase-checkout-layout">
      <div className="purchase-checkout-details">
      {prices && (
        <fieldset disabled={specLocked} className="purchase-options">
          <legend>{t.format}</legend>
          <div className="purchase-option-row">
            <label className="purchase-option">
              <input
                type="radio"
                name="purchase-fulfillment"
                checked={!digital}
                onChange={() => choose({ ...choice, fulfillment: "print" })}
              />
              <span>
                <strong>{t.printOption}</strong>
                <small>{t.printOptionHint.replace("{price}", money(order.book_price_cents))}</small>
              </span>
            </label>
            <label className="purchase-option">
              <input
                type="radio"
                name="purchase-fulfillment"
                checked={digital}
                onChange={() =>
                  choose({
                    fulfillment: "digital",
                    ebook: choice.ebook || !choice.video,
                    video: choice.video,
                  })
                }
              />
              <span>
                <strong>{t.digitalOption}</strong>
                <small>
                  {t.digitalOptionHint.replace(
                    "{price}",
                    money(prices ? Math.min(prices.digital.ebook, prices.digital.video) : null),
                  )}
                </small>
              </span>
            </label>
          </div>
          <p className="purchase-options-title">{digital ? t.digitalItems : t.extras}</p>
          <label className="purchase-option">
            <input
              type="checkbox"
              checked={choice.ebook}
              disabled={digital && choice.ebook && !choice.video}
              onChange={(e) => choose({ ...choice, ebook: e.target.checked })}
            />
            <span>
              <strong>
                {t.ebookItem} · {itemMoney(itemPrice("ebook"))}
              </strong>
              <small>{t.ebookHint}</small>
            </span>
          </label>
          <label className="purchase-option">
            <input
              type="checkbox"
              checked={choice.video}
              disabled={digital && choice.video && !choice.ebook}
              onChange={(e) => choose({ ...choice, video: e.target.checked })}
            />
            <span>
              <strong>
                {t.videoItem} · {itemMoney(itemPrice("video"))}
              </strong>
              <small>{t.videoHint}</small>
            </span>
          </label>
          <small>
            {t.bundle
              .replace("{price}", itemMoney(itemPrice("bundle")))
              .replace("{sum}", itemMoney(itemsSum))}
          </small>
          {digital && <small>{t.digitalWhy}</small>}
          {digital && choice.ebook !== choice.video && <small>{t.pickDigital}</small>}
          {!digital && <small>{t.extrasWhen}</small>}
        </fieldset>
      )}
      {!digital && (
      <fieldset disabled={specLocked} className="purchase-fields">
        <label>
          {t.size}
          <select
            value={order.book_size || "M"}
            onChange={(e) => {
              const size = e.target.value;
              void run(async () =>
                setOrder(
                  await api.setPrintSpecification(
                    projectId,
                    size,
                    order.cover_type || "soft",
                  ),
                ),
              );
            }}
          >
            <option value="M">20 × 20 cm</option>
            {order.book_size === "P" && <option value="P">15 × 15 cm</option>}
          </select>
        </label>
        <label>
          {t.cover}
          <select
            value={order.cover_type || "soft"}
            onChange={(e) => {
              const cover = e.target.value;
              void run(async () =>
                setOrder(
                  await api.setPrintSpecification(
                    projectId,
                    order.book_size || "M",
                    cover,
                  ),
                ),
              );
            }}
          >
            <option value="soft">{t.soft}</option>
            <option value="hard">{t.hard}</option>
          </select>
        </label>
        <label>
          {t.quantity}
          <input
            type="number"
            min={1}
            max={500}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            onBlur={() => {
              const n = Number(quantity);
              if (Number.isInteger(n) && n >= 1 && n <= 500 && quantityDirty)
                void run(async () =>
                  setOrder(await api.setPrintQuantity(projectId, n)),
                );
              else setQuantity(String(order.quantity));
            }}
          />
        </label>
      </fieldset>
      )}
      {!digital && (
      <form id="entrega" onSubmit={saveAddress}>
        <h4>{t.delivery}</h4>
        {order.payment_status === "paid" && !addressLocked && (
          <p className="muted">{t.editDeliveryHint}</p>
        )}
        <fieldset disabled={addressLocked} className="purchase-fields">
          {(Object.keys(empty) as (keyof PrintAddress)[]).map((key) => (
            <label key={key}>
              {
                {
                  recipient_name: t.name,
                  postal_code: t.cep,
                  street: t.street,
                  number: t.number,
                  complement: t.complement,
                  district: t.district,
                  city: t.city,
                  state: t.state,
                }[key]
              }
              <input
                required={key !== "complement"}
                value={address[key] || ""}
                maxLength={
                  key === "state" ? 2 : key === "postal_code" ? 9 : 160
                }
                autoComplete={
                  key === "postal_code"
                    ? "postal-code"
                    : key === "recipient_name"
                      ? "name"
                      : undefined
                }
                onChange={(e) =>
                  setAddress({
                    ...address,
                    [key]:
                      key === "postal_code"
                        ? formatCep(e.target.value)
                        : key === "state"
                          ? e.target.value.toUpperCase()
                          : e.target.value,
                  })
                }
              />
              {key === "postal_code" && CEP_STATUS[lang]?.[cepStatus] && (
                <small className="muted" role="status" data-testid="delivery-cep-status">
                  {CEP_STATUS[lang][cepStatus]}
                </small>
              )}
            </label>
          ))}
        </fieldset>
        <button
          className="kbtn"
          disabled={addressLocked || !addressDirty}
          type="submit"
        >
          {t.saveAddress}
        </button>
      </form>
      )}
      </div>
      <aside className="purchase-checkout-summary" aria-label={t.summary}>
      <dl className="purchase-totals">
        {digital ? (
          <div>
            <dt>{t.digitalLine}</dt>
            <dd>{money(total)}</dd>
          </div>
        ) : (
          <div>
            <dt>
              {t.book} ({order.quantity})
            </dt>
            <dd>{money(books)}</dd>
          </div>
        )}
        {extrasTotal > 0 && (
          <div>
            <dt>{extrasLabel}</dt>
            <dd>{money(extrasTotal)}</dd>
          </div>
        )}
        <div>
          <dt>{t.freight}</dt>
          <dd>{digital ? t.noFreight : t.printerFreight}</dd>
        </div>
        <div>
          <dt>{t.total}</dt>
          <dd>{money(total)}</dd>
        </div>
      </dl>
      {!digital && <p className="muted">{t.printerFreightHint}</p>}
      {order.payment_status === "paid" ? (
        <p className="purchase-payment-status is-complete" role="status">{t.paid}</p>
      ) : order.payment_status === "pending" ? (
        <>
          <p className="purchase-payment-status" role="status">{t.paymentPending}</p>
          {order.checkout_available ? (
            <button
              className="kbtn kbtn-primary"
              type="button"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const next = await api.checkoutPrint(projectId, installments);
                  setOrder(next);
                  if (next.checkout_url) window.location.assign(next.checkout_url);
                })
              }
            >
              {t.pay}
            </button>
          ) : null}
        </>
      ) : (
        <>
          {order.checkout_available ? (
            <>
              <label>
                {t.installments}
                <select
                  disabled={busy}
                  value={installments}
                  onChange={(e) => setInstallments(Number(e.target.value))}
                >
                  {Array.from({ length: 12 }, (_, i) => (
                    <option key={i} value={i + 1}>
                      {i + 1}x
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="kbtn kbtn-primary"
                type="button"
                disabled={specLocked || !ready || quantityDirty}
                onClick={() =>
                  void run(async () => {
                    const next = await api.checkoutPrint(
                      projectId,
                      installments,
                    );
                    setOrder(next);
                    if (next.checkout_url)
                      window.location.assign(next.checkout_url);
                  })
                }
              >
                {t.pay}
              </button>
            </>
          ) : canConfirmPayment ? (
            <>
              <h4>{t.confirmPayTitle}</h4>
              <p className="muted">{t.confirmPayHint}</p>
              <button
                className="kbtn kbtn-primary"
                type="button"
                disabled={specLocked || !ready || quantityDirty}
                onClick={() =>
                  void run(async () => {
                    const next = await api.confirmManualPayment(projectId);
                    setOrder(next);
                    onProject?.(await api.getProject(projectId));
                  })
                }
              >
                {t.confirmPay}
              </button>
            </>
          ) : (
            <>
              <h4>{t.quotation}</h4>
              <p className="muted">{t.unavailable}</p>
            </>
          )}
          {(!saved || addressDirty || quantityDirty) && <button
            className="kbtn kbtn-soft"
            disabled={specLocked || addressDirty || quantityDirty}
            type="button"
            onClick={() =>
              void run(async () => {
                const project = await api.saveQuotation(projectId);
                onProject?.(project);
                setSaved(true);
              })
            }
          >
            {busy ? t.wait : order.checkout_available ? t.saveForLater : t.quote}
          </button>}
        </>
      )}
      {saved && !addressDirty && !quantityDirty && <p role="status">{order.checkout_available ? t.savedForLater : t.saved}</p>}
      {order.tracking_code && (
        <p>
          {t.tracking}: <strong>{order.tracking_code}</strong>
        </p>
      )}
      {note && (
        <p role="alert" className="studio-error">
          {note}
        </p>
      )}
      </aside>
      </div>
    </section>
  );
}
