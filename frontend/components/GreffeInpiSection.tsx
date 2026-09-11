"use client";

// doc 20, doc 19 §5.3 : dossier de dépôt greffe/INPI — démo pensée pour la
// prod (pas un système à refaire) : `signerGreffeInpiChauffeur` appelle le
// même contrat d'API qu'un vrai prestataire de signature qualifiée
// brancherait plus tard (ADR-004, doc 20 §7), seule l'implémentation
// serveur (`SignatureDemoProvider`, tampon rouge « FICTIF ») est un
// bouchon. Zone de signature réelle qui finit le document — pas juste un
// badge côté React : le PDF renvoyé par `/greffe-inpi.pdf` change vraiment
// après le clic.
//
// **Déplacé le 2026-09-11** (doc 19 §2.1/§2.4, doc 17 §9 note) : cet écran
// vivait sur la fiche dossier gestionnaire, il n'a plus rien à y faire —
// c'est l'indiv, propriétaire de son dossier, qui signe. Appel authentifié
// (`lib/auth-chauffeur.ts`) pour que `demo_api.py` attribue vraiment
// `signataire` à l'indiv connecté, pas au stub `UTILISATEUR_DEMO`.
//
// **Bouton plutôt que `<a href>` pour le PDF, même jour** (doc 19 §8bis) :
// cette route exige aussi un jeton désormais — un lien direct échouerait
// en 401.
import { useState } from "react";

import { ApiError, cheminGreffeInpi } from "@/lib/api";
import {
  ErreurAuthChauffeur,
  signerGreffeInpiChauffeur,
  telechargerAvecAuthChauffeur,
} from "@/lib/auth-chauffeur";
import type { DossierResume } from "@/lib/types";

import { Badge } from "./Badge";

// `signerGreffeInpiChauffeur` lève `ErreurAuthChauffeur` (pas de session)
// ou `ApiError` (réponse HTTP non-ok) ; `telechargerAvecAuthChauffeur` ne
// lève que `ErreurAuthChauffeur` dans les deux cas (lib/auth-chauffeur.ts).
function messageErreur(exception: unknown, repli: string): string {
  return exception instanceof ErreurAuthChauffeur || exception instanceof ApiError
    ? exception.message
    : repli;
}

export function GreffeInpiSection({ dossier }: { dossier: DossierResume }) {
  // État local plutôt que remonté au parent (doc 19 §5 : la page chauffeur
  // gère déjà son propre état pour les transactions de la même façon) —
  // ce composant n'a besoin de rien d'autre que son propre statut signé.
  const [signe, setSigne] = useState(dossier.greffe_inpi_signe);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function signer() {
    setEnCours(true);
    setErreur(null);
    try {
      await signerGreffeInpiChauffeur(dossier.dossier_id);
      setSigne(true);
    } catch (exception) {
      setErreur(messageErreur(exception, "Échec de la signature."));
    } finally {
      setEnCours(false);
    }
  }

  async function telecharger() {
    setErreur(null);
    try {
      await telechargerAvecAuthChauffeur(
        cheminGreffeInpi(dossier.dossier_id),
        `greffe-inpi-${dossier.dossier_id}.pdf`,
      );
    } catch (exception) {
      setErreur(messageErreur(exception, "Échec du téléchargement."));
    }
  }

  return (
    <div className="mb-6 rounded-lg border border-border bg-canvas p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-subtle">
          Dépôt greffe/INPI — comptes annuels
        </h2>
        {signe ? (
          <Badge variant="validated">signé</Badge>
        ) : (
          <Badge variant="pending">non signé</Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => void telecharger()}
          className="text-sm text-primary hover:underline"
        >
          Dossier de dépôt (PDF)
        </button>
        {!signe && (
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
