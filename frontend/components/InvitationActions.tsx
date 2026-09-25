"use client";

import { useState } from "react";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { inviterChauffeur } from "@/lib/auth-gestionnaire";
import type { DossierAgregat } from "@/lib/types";

/** doc 17 §9 bloc B, doc 19 §3.2 : visibilité de premier rang sur
 * l'onboarding du chauffeur — jamais caché dans un écran de paramètres.
 * Envoie une vraie invitation par e-mail via Supabase Auth (pas de
 * simulateur). Empêche la navigation du `<Link>` de la carte dossier
 * (`stopPropagation`) : ce widget vit dans une carte cliquable, mais ses
 * propres contrôles ne doivent pas déclencher la navigation. */
export function InvitationActions({
  dossier,
  onInvite,
}: {
  dossier: DossierAgregat;
  onInvite: () => void;
}) {
  const [email, setEmail] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  if (dossier.statut_invitation === "actif") {
    return <Badge variant="validated">Compte ouvert</Badge>;
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
      onInvite();
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
      <Input
        type="email"
        value={email}
        onChange={(evenement) => setEmail(evenement.target.value)}
        placeholder="E-mail du chauffeur"
        disabled={enCours}
        className="h-7 w-40 text-xs"
      />
      <Button
        type="submit"
        variant="secondary"
        size="sm"
        disabled={enCours || !email.trim()}
      >
        Inviter
      </Button>
      {erreur && <p className="text-xs text-danger">{erreur}</p>}
    </form>
  );
}
