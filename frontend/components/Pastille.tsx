export type TonPastille = "positif" | "attention" | "negatif" | "neutre" | "absent";

const STYLES: Record<TonPastille, string> = {
  positif: "bg-validated-subtle text-validated",
  attention: "bg-pending-subtle text-[#8a4b00]",
  negatif: "bg-[#fcedee] text-danger",
  neutre: "bg-surface-soft text-subtle",
  absent: "border border-dashed border-border-strong text-muted",
};

/** État d'un objet en un mot : pastille à coins serrés, point de couleur
 * optionnel. Pour les statuts du gestionnaire (compte, connexion, canal). */
export function Pastille({
  ton,
  point = false,
  children,
}: {
  ton: TonPastille;
  point?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-sm px-2 text-xs font-medium ${STYLES[ton]}`}
    >
      {point && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}
