"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/Badge";
import { ApiError, inviterChauffeur } from "@/lib/api";
import type { DossierResume } from "@/lib/types";

/** doc 17 §9 bloc B, doc 19 §3.2 : visibilité de premier rang sur
 * l'onboarding du chauffeur — jamais caché dans un écran de paramètres.
 * Envoie une vraie invitation par e-mail via Supabase Auth (pas de
 * simulateur). Empêche la navigation du `<Link>` de la carte dossier
 * (`stopPropagation`) : ce widget vit dans une carte cliquable, mais ses
 * propres contrôles ne doivent pas déclencher la navigation. */
export function InvitationActions({ dossier }: { dossier: DossierResume }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  if (dossier.statut_invitation === "actif") {
    return <Badge variant="validated">Chauffeur actif</Badge>;
  }
  if (dossier.statut_invitation === "invité") {
    return <Badge variant="pending">Invitation envoyée</Badge>;
  }

  async function inviter(evenement: React.FormEvent) {
    evenement.preventDefault();
    evenement.stopPropagation();
    if (!email.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      await inviterChauffeur(dossier.dossier_id, email.trim());
      router.refresh();
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'invitation.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <form
      className="flex items-center gap-1"
      onClick={(evenement) => evenement.stopPropagation()}
      onSubmit={inviter}
    >
      <input
        type="email"
        value={email}
        onChange={(evenement) => setEmail(evenement.target.value)}
        placeholder="e-mail du chauffeur…"
        disabled={enCours}
        className="w-40 rounded-md border border-border px-2 py-1 text-xs"
      />
      <button
        type="submit"
        disabled={enCours || !email.trim()}
        className="rounded-md border border-border px-2 py-1 text-xs font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
      >
        Inviter
      </button>
      {erreur && <p className="text-xs text-danger">{erreur}</p>}
    </form>
  );
}
