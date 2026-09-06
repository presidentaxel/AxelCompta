/** Vocabulaire de badge unique (doc 11 §4, DESIGN.md « badges de statut ») :
 * pas de badge ad hoc — "à trancher" réutilise le token sémantique
 * `pending` (en attente de décision) plutôt que d'inventer une couleur.
 */
export type BadgeVariant = "validated" | "pending" | "danger" | "neutral";

const STYLES: Record<BadgeVariant, string> = {
  validated: "bg-validated-subtle text-validated border border-success/30",
  pending: "bg-pending-subtle text-pending border border-warning/30",
  danger: "bg-danger-subtle text-danger border border-danger/30",
  neutral: "bg-surface-soft text-subtle border border-border",
};

export function Badge({
  variant,
  children,
}: {
  variant: BadgeVariant;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STYLES[variant]}`}
    >
      {children}
    </span>
  );
}
