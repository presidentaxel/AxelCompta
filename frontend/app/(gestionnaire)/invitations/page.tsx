"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { InvitationActions } from "@/components/InvitationActions";
import { InvitationsEnMasse } from "@/components/InvitationsEnMasse";
import { ErreurAuthGestionnaire, listerDossiers } from "@/lib/auth-gestionnaire";
import type { DossierAgregat } from "@/lib/types";

/** Invitation individuelle ou en masse (doc 19 §3.1). Hors du tableau de
 * bord : ce n'est pas le geste le plus fréquent. */
export default function InvitationsPage() {
  const router = useRouter();
  const [dossiers, setDossiers] = useState<DossierAgregat[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [choisi, setChoisi] = useState("");

  const charger = useCallback(() => {
    listerDossiers()
      .then((liste) => {
        setDossiers(liste);
        setChoisi((actuel) => {
          const encore = liste.some(
            (dossier) => dossier.dossier_id === actuel && dossier.statut_invitation === null,
          );
          if (encore) return actuel;
          return liste.find((dossier) => dossier.statut_invitation === null)?.dossier_id ?? "";
        });
      })
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) {
          router.replace("/connexion");
        } else {
          setErreur("Impossible de charger les chauffeurs.");
        }
      });
  }, [router]);

  useEffect(charger, [charger]);

  const sansCompte = dossiers?.filter((dossier) => dossier.statut_invitation === null) ?? [];
  const enAttente = dossiers?.filter((dossier) => dossier.statut_invitation === "invité") ?? [];
  const dossierChoisi = sansCompte.find((dossier) => dossier.dossier_id === choisi) ?? null;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Invitations</h1>
      <p className="mt-2 text-sm text-subtle">Ouvrir un compte pour un chauffeur.</p>
      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      {!dossiers && !erreur && <p className="mt-8 text-sm text-subtle">Chargement…</p>}

      {dossiers && sansCompte.length === 0 && (
        <p className="mt-8 text-sm text-subtle">Tous les chauffeurs ont déjà un compte ou une invitation.</p>
      )}
      {dossierChoisi && (
        <div className="mt-8 space-y-3">
          <label className="block text-sm font-medium text-ink" htmlFor="chauffeur">
            Chauffeur
          </label>
          <select
            id="chauffeur"
            value={choisi}
            onChange={(evenement) => setChoisi(evenement.target.value)}
            className="h-9 w-full rounded-md border border-border bg-canvas px-3 text-sm text-ink outline-none focus-visible:border-border-focus focus-visible:shadow-[0_0_0_3px_rgba(37,99,235,0.12)]"
          >
            {sansCompte.map((dossier) => (
              <option key={dossier.dossier_id} value={dossier.dossier_id}>
                {dossier.nom}
              </option>
            ))}
          </select>
          <InvitationActions dossier={dossierChoisi} onInvite={charger} />
        </div>
      )}

      {enAttente.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm font-semibold text-ink">En attente de réponse</h2>
          <ul className="mt-3">
            {enAttente.map((dossier) => (
              <li key={dossier.dossier_id} className="border-b border-hairline py-3 text-sm text-ink">
                {dossier.nom}
              </li>
            ))}
          </ul>
        </section>
      )}

      {dossiers && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-ink">Plusieurs à la fois</h2>
          <div className="mt-3">
            <InvitationsEnMasse onTermine={charger} />
          </div>
        </section>
      )}
    </div>
  );
}
