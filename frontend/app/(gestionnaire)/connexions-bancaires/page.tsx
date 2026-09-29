"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  type ConnexionDossier,
  type ConnexionsBancaires,
  ErreurAuthGestionnaire,
  lireConnexionsBancaires,
  type ModeRelance,
  reglerRelanceDossier,
  reglerRelancePortefeuille,
} from "@/lib/auth-gestionnaire";
import { Pastille } from "@/components/Pastille";
import { Segments } from "@/components/Segments";
import { formatDate } from "@/lib/format";

const STATUTS: Record<ConnexionDossier["statut"], string> = {
  expire: "Expirée",
  a_renouveler: "À renouveler",
  jamais_connecte: "Jamais connectée",
  actif: "Active",
};

const SANTES: Partial<Record<ConnexionDossier["sante"], string>> = {
  auth_requise: "La banque demande de confirmer",
  sans_acces: "Accès aux données coupé",
  en_pause: "En pause",
};

const MODES: { mode: ModeRelance; titre: string; detail: string }[] = [
  {
    mode: "auto",
    titre: "Automatique",
    detail:
      "AxeLCompta prévient le chauffeur dans son application : deux semaines avant, une semaine avant, à l'expiration, puis tous les 3 jours.",
  },
  {
    mode: "manuel",
    titre: "Manuel",
    detail: "Rien n'est envoyé au chauffeur. Vous suivez cette page et le contactez vous-même.",
  },
];

/** doc 14 §2.2 et §2.3 : l'état des connexions bancaires, écran de premier
 * rang, et le mode de relance du portefeuille ou d'un dossier. */
export default function ConnexionsBancairesPage() {
  const router = useRouter();
  const [donnees, setDonnees] = useState<ConnexionsBancaires | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = useCallback(() => {
    lireConnexionsBancaires()
      .then(setDonnees)
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) router.replace("/connexion");
        else setErreur("Impossible de charger les connexions bancaires.");
      });
  }, [router]);

  useEffect(() => {
    charger();
  }, [charger]);

  async function regler(action: () => Promise<void>) {
    setEnCours(true);
    setErreur(null);
    try {
      await action();
      charger();
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Réglage refusé.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <h1 className="text-[22px] font-medium tracking-tight text-ink">Connexions bancaires</h1>
      <p className="mt-1 text-[13.5px] text-subtle">
        Sans connexion valide, les opérations d&apos;un chauffeur n&apos;arrivent plus.
      </p>
      {erreur && <p className="mt-4 text-sm text-danger">{erreur}</p>}
      {donnees && (
        <>
          <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-3">
            <Compteur libelle="Expirées" valeur={donnees.compteurs.expire} alerte />
            <Compteur libelle="À confirmer" valeur={donnees.a_reconnecter} alerte />
            <Compteur libelle="À renouveler (14 jours)" valeur={donnees.compteurs.a_renouveler} />
            <Compteur libelle="Actives" valeur={donnees.compteurs.actif} />
            <Compteur libelle="Jamais connectées" valeur={donnees.compteurs.jamais_connecte} />
          </dl>

          <section className="mt-7 flex items-center gap-6 rounded-[10px] border border-border bg-canvas px-4 py-3.5">
            <div className="min-w-0 flex-1">
              <h2 className="text-[15px] font-medium text-ink">Relances des chauffeurs</h2>
              <p className="mt-0.5 text-[13px] text-subtle">
                {MODES.find(({ mode }) => mode === donnees.relance_portefeuille)?.detail}
              </p>
            </div>
            <div className="w-64 shrink-0">
              <Segments
                valeur={donnees.relance_portefeuille}
                onChange={(mode) => {
                  if (!enCours && mode !== donnees.relance_portefeuille) {
                    void regler(() => reglerRelancePortefeuille(mode));
                  }
                }}
                options={MODES.map(({ mode, titre }) => ({ valeur: mode, libelle: titre }))}
              />
            </div>
          </section>

          <table className="mt-7 w-full border-collapse text-left text-[13.5px]">
            <thead>
              <tr className="border-b border-border text-[11.5px] font-medium tracking-wide text-muted">
                <th className="w-[26%] pb-2 pr-3">Entreprise</th>
                <th className="w-[26%] pb-2 pr-3">Connexion</th>
                <th className="pb-2 pr-3">Expire le</th>
                <th className="pb-2 pr-3">Dernière mise à jour</th>
                <th className="pb-2">Relances</th>
              </tr>
            </thead>
            <tbody>
              {donnees.dossiers.map((dossier) => (
                <tr key={dossier.dossier_id} className="border-b border-hairline align-top">
                  <td className="py-3 pr-3 font-medium text-ink">{dossier.nom}</td>
                  <td className="py-3 pr-3">
                    <Etat dossier={dossier} />
                  </td>
                  <td className="py-3 pr-3 tabular-nums text-ink">
                    {dossier.expire_le ? formatDate(dossier.expire_le) : <span className="text-muted">-</span>}
                    {dossier.jours_restants !== null && dossier.jours_restants >= 0 && (
                      <span className="block text-xs text-muted">
                        dans {dossier.jours_restants} jour{dossier.jours_restants > 1 ? "s" : ""}
                      </span>
                    )}
                  </td>
                  <td className="py-3 pr-3 tabular-nums text-subtle">
                    {dossier.dernier_rafraichissement ? (
                      formatDate(dossier.dernier_rafraichissement)
                    ) : (
                      <span className="text-muted">-</span>
                    )}
                  </td>
                  <td className="py-3">
                    <select
                      aria-label={`Relances pour ${dossier.nom}`}
                      disabled={enCours}
                      value={dossier.relance_propre ? dossier.relance : "portefeuille"}
                      onChange={(evenement) => {
                        const valeur = evenement.target.value;
                        void regler(() =>
                          reglerRelanceDossier(
                            dossier.dossier_id,
                            valeur === "portefeuille" ? null : (valeur as ModeRelance),
                          ),
                        );
                      }}
                      className="w-full max-w-52 rounded-md border border-border-strong bg-canvas px-2.5 text-ink"
                    >
                      <option value="portefeuille">
                        Comme le portefeuille ({donnees.relance_portefeuille === "auto" ? "automatique" : "manuel"})
                      </option>
                      <option value="auto">Automatique</option>
                      <option value="manuel">Manuel</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function Compteur({ libelle, valeur, alerte = false }: { libelle: string; valeur: number; alerte?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-muted">{libelle}</dt>
      <dd
        className={`mt-0.5 text-[22px] font-normal tabular-nums tracking-tight ${alerte && valeur > 0 ? "text-danger" : "text-ink"}`}
      >
        {valeur}
      </dd>
    </div>
  );
}

function Etat({ dossier }: { dossier: ConnexionDossier }) {
  const probleme = SANTES[dossier.sante];
  const urgent = dossier.statut === "expire" || dossier.sante === "auth_requise";
  const ton =
    dossier.statut === "jamais_connecte"
      ? "absent"
      : urgent
        ? "negatif"
        : dossier.statut === "a_renouveler"
          ? "attention"
          : "positif";
  return (
    <span className="block">
      <Pastille ton={ton} point={ton !== "absent"}>
        {dossier.sante === "auth_requise" ? "À confirmer" : STATUTS[dossier.statut]}
      </Pastille>
      {probleme && <span className={`mt-1 block text-xs ${urgent ? "text-danger" : "text-muted"}`}>{probleme}</span>}
    </span>
  );
}
