import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge } from "@/components/Badge";
import { listerTransactions, obtenirDossier } from "@/lib/api";
import { formatMontant } from "@/lib/format";
import type { TransactionVue } from "@/lib/types";

export default async function DossierPage({ params }: { params: { id: string } }) {
  const dossier = await obtenirDossier(params.id).catch(() => null);
  if (dossier === null) {
    notFound();
  }
  const transactions = await listerTransactions(params.id);

  return (
    <div className="mx-auto max-w-5xl">
      <Link href="/" className="text-sm text-primary hover:underline">
        ← Tableau de bord
      </Link>
      <div className="mt-2 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">{dossier.nom}</h1>
        <Badge variant="neutral">{dossier.tva_recettes_regime}</Badge>
      </div>
      <p className="mb-6 text-sm text-subtle">
        {dossier.exercice_debut} → {dossier.exercice_fin} · {dossier.nb_transactions} écritures
      </p>

      <div className="overflow-hidden rounded-lg border border-border bg-canvas">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-canvas-app text-xs uppercase tracking-wide text-subtle">
              <th className="px-4 py-2 text-left font-semibold">Date</th>
              <th className="px-4 py-2 text-left font-semibold">Libellé</th>
              <th className="px-4 py-2 text-left font-semibold">Compte</th>
              <th className="px-4 py-2 text-right font-semibold">Montant</th>
              <th className="px-4 py-2 text-left font-semibold">Statut</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction) => (
              <TransactionRow key={transaction.ecriture_id} transaction={transaction} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TransactionRow({ transaction }: { transaction: TransactionVue }) {
  const negatif = transaction.montant_cts < 0;
  const aTrancher = transaction.statut === "à trancher";
  return (
    <tr className={`border-t border-border hover:bg-canvas-app ${aTrancher ? "bg-pending-subtle/40" : ""}`}>
      <td className="px-4 py-2 text-subtle">{transaction.date}</td>
      <td className="px-4 py-2 text-ink">{transaction.libelle}</td>
      <td className="px-4 py-2 font-mono text-xs text-subtle">{transaction.compte}</td>
      <td
        className={`px-4 py-2 text-right tabular-nums font-medium ${
          negatif ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(transaction.montant_cts)}
      </td>
      <td className="px-4 py-2">
        <Badge variant={aTrancher ? "pending" : "validated"}>{transaction.statut}</Badge>
      </td>
    </tr>
  );
}
