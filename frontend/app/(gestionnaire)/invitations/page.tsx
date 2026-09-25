"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { InvitationsEnMasse } from "@/components/InvitationsEnMasse";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ErreurAuthGestionnaire,
  inviterChauffeur,
  listerDossiers,
} from "@/lib/auth-gestionnaire";
import { libelleCompte } from "@/lib/dossier-libelles";
import type { DossierAgregat } from "@/lib/types";

/** Une ligne par entreprise sans compte, plus un collage pour plusieurs.
 * Plus de liste déroulante : l'e-mail se saisit en face du nom. */
export default function InvitationsPage() {
  const router = useRouter();
  const [dossiers, setDossiers] = useState<DossierAgregat[] | null>(null);
  const [emails, setEmails] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);

  const charger = useCallback(() => {
    listerDossiers()
      .then(setDossiers)
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) {
          router.replace("/connexion");
        } else {
          setErreur("Impossible de charger les entreprises.");
        }
      });
  }, [router]);

  useEffect(charger, [charger]);

  const sansCompte = dossiers?.filter((dossier) => dossier.statut_invitation === null) ?? [];
  const suivies =
    dossiers?.filter((dossier) => dossier.statut_invitation === "invité" || dossier.statut_invitation === "actif") ??
    [];

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Invitations</h1>
      <p className="mt-2 text-sm text-subtle">
        Saisis l&apos;e-mail en face de chaque entreprise, ou colle une liste nom, e-mail.
      </p>
      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      {!dossiers && !erreur && <p className="mt-8 text-sm text-subtle">Chargement…</p>}

      {dossiers && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-ink">Plusieurs à la fois</h2>
          <div className="mt-3">
            <InvitationsEnMasse dossiers={dossiers} onTermine={charger} />
          </div>
        </section>
      )}

      {sansCompte.length > 0 && (
        <ul className="mt-10">
          {sansCompte.map((dossier) => (
            <li key={dossier.dossier_id} className="flex items-center gap-3 border-b border-hairline py-3">
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{dossier.nom}</span>
              <Input
                type="email"
                value={emails[dossier.dossier_id] ?? ""}
                onChange={(evenement) =>
                  setEmails((actuel) => ({ ...actuel, [dossier.dossier_id]: evenement.target.value }))
                }
                placeholder="E-mail"
                className="max-w-56"
                aria-label={`E-mail de ${dossier.nom}`}
              />
              <Button
                type="button"
                size="sm"
                disabled={enCours === dossier.dossier_id || !(emails[dossier.dossier_id] ?? "").includes("@")}
                onClick={async () => {
                  setEnCours(dossier.dossier_id);
                  setErreur(null);
                  try {
                    await inviterChauffeur(dossier.dossier_id, emails[dossier.dossier_id] ?? "");
                    charger();
                  } catch (exception) {
                    setErreur(exception instanceof Error ? exception.message : "Échec de l'invitation.");
                  } finally {
                    setEnCours(null);
                  }
                }}
              >
                Inviter
              </Button>
            </li>
          ))}
        </ul>
      )}
      {dossiers && sansCompte.length === 0 && (
        <p className="mt-8 text-sm text-subtle">Toutes les entreprises ont déjà une invitation.</p>
      )}

      {suivies.length > 0 && (
        <section className="mt-10">
          <h2 className="text-sm font-semibold text-ink">Déjà lancées</h2>
          <ul className="mt-3">
            {suivies.map((dossier) => (
              <li key={dossier.dossier_id} className="flex justify-between border-b border-hairline py-3 text-sm">
                <span className="text-ink">{dossier.nom}</span>
                <span className="text-subtle">{libelleCompte(dossier.statut_invitation)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
