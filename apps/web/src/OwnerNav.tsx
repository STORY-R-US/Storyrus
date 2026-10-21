const ITEMS = [
  { href: "/gastos", id: "gastos", label: "Gastos" },
  { href: "/pedidos", id: "pedidos", label: "Pedidos" },
  { href: "/usuarios", id: "usuarios", label: "Usuários" },
] as const;

export type OwnerPanel = (typeof ITEMS)[number]["id"];

export function OwnerNav({ current }: { current: OwnerPanel }) {
  return (
    <nav className="usage-owner-nav" aria-label="Painéis do dono" data-testid="owner-nav">
      <a href="/" data-testid="owner-nav-home">
        Início
      </a>
      {ITEMS.map((item) => (
        <a
          key={item.id}
          href={item.href}
          className={item.id === current ? "is-on" : undefined}
          aria-current={item.id === current ? "page" : undefined}
        >
          {item.label}
        </a>
      ))}
    </nav>
  );
}
