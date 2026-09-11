"use client";

// doc 20, Louis 2026-09-11 : dossier de dépôt greffe/INPI — démo pensée
// pour la prod (pas un système à refaire) : `signerGreffeInpi` appelle le
// même contrat d'API qu'un vrai prestataire de signature qualifiée
// brancherait plus tard (ADR-004, doc 20 §7), seule l'implémentation
// serveur (`SignatureDemoProvider`, tampon rouge « FICTIF ») est un
// bouchon. Zone de signature réelle qui finit le document — pas juste un
// badge côté React (même principe que TrancherActions, doc 17 §9 bloc C) :
// le PDF renvoyé par `/greffe-inpi.pdf` change vraiment après le clic.
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, signerGreffeInpi, urlGreffeInpi } from "@/lib/api";
import type { DossierResume } from "@/lib/types";

import { Badge } from "./Badge";

export function GreffeInpiSection({ dossier }: { dossier: DossierResume }) {
  const router = useRouter();
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function signer() {
    setEnCours(true);
    setErreur(null);
    try {
      await signerGreffeInpi(dossier.dossier_id);
      router.refresh();
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de la signature.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="mb-6 rounded-lg border border-border bg-canvas p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-subtle">
          Dépôt greffe/INPI — comptes annuels
        </h2>
        {dossier.greffe_inpi_signe ? (
          <Badge variant="validated">signé</Badge>
        ) : (
          <Badge variant="pending">non signé</Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <a
          href={urlGreffeInpi(dossier.dossier_id)}
          className="text-sm text-primary hover:underline"
        >
          Dossier de dépôt (PDF)
        </a>
        {!dossier.greffe_inpi_signe && (
          <button
            type="button"
            disabled={enCours}
            onClick={() => void signer()}
            className="rounded-md border border-border px-3 py-1 text-sm font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
          >
            Signer (démo)
          </button>
        )}
      </div>
      {erreur && <p className="mt-2 text-xs text-danger">{erreur}</p>}
      <p className="mt-3 text-xs text-subtle">
        Démo — signature fictive, jamais une vraie signature qualifiée RGS (doc 20 §4). Le vrai
        dépôt reste bloqué sur le choix d&apos;un prestataire (ADR-004).
      </p>
    </div>
  );
}
