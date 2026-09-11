"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ClotureSection } from "@/components/ClotureSection";
import { GreffeInpiSection } from "@/components/GreffeInpiSection";
import { JustificatifPhoto } from "@/components/JustificatifPhoto";
import { QuestionCategorisation } from "@/components/QuestionCategorisation";
import { SignatureMock } from "@/components/SignatureMock";
import { fetchAvecAuthChauffeur, obtenirSession } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";
import type { DossierResume, TransactionVue } from "@/lib/types";

type Chargement =
  | { statut: "en_cours" }
  | { statut: "pret"; dossier: DossierResume; transactions: TransactionVue[] }
  | { statut: "erreur"; message: string };

/** Vue chauffeur (doc 19 §5.5 : « vocabulaire simple, pas le vocabulaire
 * comptable pro »). doc 17 §9 Semaine 3 : transactions catégorisées,
 * question de catégorisation (usage_personnel ou non,
 * `QuestionCategorisation`), photo de justificatif (`JustificatifPhoto`,
 * pas d'OCR) et signature mockée (`SignatureMock`, « vrai faux », décidé
 * 2026-09-07).
 *
 * **Depuis le 2026-09-11** (doc 19 §2.1/§5.3) : clôture (`ClotureSection`)
 * et dépôt greffe/INPI (`GreffeInpiSection`) ont migré ici depuis la fiche
 * dossier gestionnaire — c'est l'indiv, propriétaire de son dossier, qui
 * les voit et qui signe, jamais le gestionnaire (doc 19 §2.4).
 */
export default function DossierChauffeurPage({ params }: { params: { dossierId: string } }) {
  const router = useRouter();
  const [chargement, setChargement] = useState<Chargement>({ statut: "en_cours" });

  useEffect(() => {
    const session = obtenirSession();
    if (session === null) {
      router.push("/chauffeur/login");
      return;
    }
    if (session.dossierId !== params.dossierId) {
      // Pas une 403 muette : on renvoie vers le seul dossier auquel ce
      // compte a effectivement accès (doc 19 §4).
      router.replace(`/chauffeur/${session.dossierId}`);
      return;
    }
    Promise.all([
      fetchAvecAuthChauffeur<DossierResume>(`/dossiers/${params.dossierId}`),
      fetchAvecAuthChauffeur<TransactionVue[]>(`/dossiers/${params.dossierId}/transactions`),
    ])
      .then(([dossier, transactions]) => setChargement({ statut: "pret", dossier, transactions }))
      .catch(() => setChargement({ statut: "erreur", message: "Impossible de charger vos données." }));
  }, [params.dossierId, router]);

  function remplacerTransaction(transaction: TransactionVue) {
    setChargement((etat) =>
      etat.statut === "pret"
        ? {
            ...etat,
            transactions: etat.transactions.map((t) =>
              t.ecriture_id === transaction.ecriture_id ? transaction : t,
            ),
          }
        : etat,
    );
  }

  if (chargement.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (chargement.statut === "erreur") {
    return <p className="text-sm text-danger">{chargement.message}</p>;
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-ink">Bonjour {chargement.dossier.nom}</h1>
      <p className="mb-3 text-sm text-subtle">Voici vos dernières transactions.</p>
      <ConnexionBancaireBadge mode={chargement.dossier.mode_acces_bancaire} />
      <div className="mt-4">
        <ClotureSection dossier={chargement.dossier} />
        <GreffeInpiSection dossier={chargement.dossier} />
      </div>
      <ul className="mt-4 space-y-2">
        {chargement.transactions.map((transaction) => (
          <TransactionLigne
            key={transaction.ecriture_id}
            dossierId={params.dossierId}
            transaction={transaction}
            onChange={remplacerTransaction}
          />
        ))}
      </ul>
      <div className="mt-6">
        <SignatureMock nomDocument="Liasse de l'exercice en cours" />
      </div>
    </div>
  );
}

function ConnexionBancaireBadge({ mode }: { mode: DossierResume["mode_acces_bancaire"] }) {
  if (mode === "gestionnaire") {
    return (
      <p className="text-xs text-subtle">
        Connexion bancaire : gérée par votre gestionnaire, rien à faire de votre côté.
      </p>
    );
  }
  return (
    <div className="flex items-center gap-2 text-xs text-subtle">
      <span>Connexion bancaire : à relier vous-même.</span>
      <button
        type="button"
        disabled
        title="Bientôt disponible — doc 19 §4"
        className="rounded-md border border-border px-2 py-0.5 font-semibold text-subtle opacity-60"
      >
        Connecter ma banque (bientôt)
      </button>
    </div>
  );
}

function TransactionLigne({
  dossierId,
  transaction,
  onChange,
}: {
  dossierId: string;
  transaction: TransactionVue;
  onChange: (transaction: TransactionVue) => void;
}) {
  const negatif = transaction.montant_cts < 0;
  const aVerifier = transaction.statut === "à trancher";
  return (
    <li className="rounded-md border border-border bg-canvas px-3 py-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-ink">{transaction.libelle}</p>
          <p className="text-xs text-subtle">
            {transaction.date} · {aVerifier ? "à vérifier" : "traité"}
          </p>
        </div>
        <span
          className={`tabular-nums text-sm font-medium ${
            negatif ? "text-amount-negative" : "text-amount-positive"
          }`}
        >
          {formatMontant(transaction.montant_cts)}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-2">
        <JustificatifPhoto
          dossierId={dossierId}
          ecritureId={transaction.ecriture_id}
          aJustificatif={transaction.a_justificatif}
          onJointe={onChange}
        />
        {aVerifier && (
          <div className="w-full sm:w-auto sm:flex-1">
            <QuestionCategorisation
              dossierId={dossierId}
              ecritureId={transaction.ecriture_id}
              onResolu={onChange}
            />
          </div>
        )}
      </div>
    </li>
  );
}
