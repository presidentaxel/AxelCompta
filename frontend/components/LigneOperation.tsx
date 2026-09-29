import { formatMontant } from "@/lib/format";
import { libelleJourCourt, presenter } from "@/lib/operations-chauffeur";
import type { TransactionVue } from "@/lib/types";

/** Une opération sur une ligne : nom, date et catégorie si elle est connue,
 * montant à droite. Toute la ligne s'ouvre. */
export function LigneOperation({
  transaction,
  avecDate = false,
  onOuvrir,
}: {
  transaction: TransactionVue;
  avecDate?: boolean;
  onOuvrir: (transaction: TransactionVue) => void;
}) {
  const { nom, detail } = presenter(transaction.libelle);
  const negatif = transaction.montant_cts < 0;
  const sousTitre = [
    avecDate ? libelleJourCourt(transaction.date) : null,
    transaction.statut === "à trancher" ? null : detail,
  ]
    .filter((morceau): morceau is string => morceau !== null)
    .join(" - ");
  return (
    <button
      type="button"
      onClick={() => onOuvrir(transaction)}
      className="flex w-full items-center justify-between gap-4 border-b border-hairline py-3 text-left last:border-b-0"
    >
      <span className="min-w-0">
        <span className="block truncate text-[15px] font-medium text-ink">{nom}</span>
        {sousTitre && <span className="mt-0.5 block truncate text-xs text-muted">{sousTitre}</span>}
      </span>
      <span
        className={`shrink-0 text-[15px] font-medium tabular-nums ${
          negatif ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(transaction.montant_cts)}
      </span>
    </button>
  );
}
