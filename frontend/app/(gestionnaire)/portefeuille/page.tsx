"use client";

import { Bell, Mail, Plug, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  declencherRappel,
  ErreurAuthGestionnaire,
  lirePortefeuilleSession,
  listerDossiers,
  listerRegles,
  retirerDossier,
  type RegleRappel,
} from "@/lib/auth-gestionnaire";
import {
  libelleBanque,
  libelleCompte,
  libelleImposition,
  libelleRegimeTva,
  libelleTvaRecettes,
} from "@/lib/dossier-libelles";
import { formatDate, formatMontant } from "@/lib/format";
import type { DossierAgregat } from "@/lib/types";

type FiltreCompte = "tous" | "sans_compte" | "invite" | "ouvert";
type FiltreResultat = "tous" | "negatif" | "positif";

export default function PortefeuillePage() {
  const router = useRouter();
  const [dossiers, setDossiers] = useState<DossierAgregat[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");
  const [compte, setCompte] = useState<FiltreCompte>("tous");
  const [resultat, setResultat] = useState<FiltreResultat>("tous");
  const [forme, setForme] = useState("toutes");
  const [tva, setTva] = useState("toutes");
  const [selection, setSelection] = useState<string | null>(null);
  const [regles, setRegles] = useState<RegleRappel[]>([]);
  const [infoRappel, setInfoRappel] = useState<string | null>(null);

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

  useEffect(() => {
    const memo = lirePortefeuilleSession();
    // Lecture de sessionStorage avant le rafraîchissement réseau.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (memo) setDossiers(memo);
    charger();
    listerRegles().then(setRegles).catch(() => setRegles([]));
  }, [charger]);

  const formes = useMemo(
    () => [...new Set((dossiers ?? []).map((dossier) => dossier.forme_juridique))].sort(),
    [dossiers],
  );
  const tvas = useMemo(
    () => [...new Set((dossiers ?? []).map((dossier) => dossier.tva_recettes_regime))].sort(),
    [dossiers],
  );

  const visibles = useMemo(() => {
    const aiguille = recherche.trim().toLowerCase();
    return (dossiers ?? []).filter((dossier) => {
      if (compte === "sans_compte" && dossier.statut_invitation !== null) return false;
      if (compte === "invite" && dossier.statut_invitation !== "invité") return false;
      if (compte === "ouvert" && dossier.statut_invitation !== "actif") return false;
      if (resultat === "negatif" && dossier.resultat_cts >= 0) return false;
      if (resultat === "positif" && dossier.resultat_cts < 0) return false;
      if (forme !== "toutes" && dossier.forme_juridique !== forme) return false;
      if (tva !== "toutes" && dossier.tva_recettes_regime !== tva) return false;
      if (!aiguille) return true;
      return `${dossier.nom} ${dossier.plateformes.join(" ")}`.toLowerCase().includes(aiguille);
    });
  }, [compte, dossiers, forme, recherche, resultat, tva]);

  const totaux = useMemo(() => {
    const liste = dossiers ?? [];
    return {
      nombre: liste.length,
      sansCompte: liste.filter((dossier) => dossier.statut_invitation === null).length,
      resultat: liste.reduce((somme, dossier) => somme + dossier.resultat_cts, 0),
    };
  }, [dossiers]);

  const choisi = dossiers?.find((dossier) => dossier.dossier_id === selection) ?? null;

  return (
    <div className="-m-8 flex min-h-screen">
    <div className="mx-auto min-w-0 max-w-3xl flex-1 p-8">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Entreprises</h1>
      {dossiers && (
        <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-4">
          <Total libelle="Entreprises" valeur={String(totaux.nombre)} />
          <Total libelle="Sans compte" valeur={String(totaux.sansCompte)} />
          <Total libelle="Résultat" valeur={formatMontant(totaux.resultat)} montant={totaux.resultat} />
        </dl>
      )}

      <div className="mt-8 flex items-center gap-2">
        <Input
          value={recherche}
          onChange={(evenement) => setRecherche(evenement.target.value)}
          placeholder="Rechercher une entreprise"
          aria-label="Rechercher une entreprise"
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Bascule
          libelle="Compte"
          valeur={compte}
          options={ORDRE_COMPTE.map((id) => ({ id, libelle: LIBELLES_COMPTE[id] }))}
          onChoisir={setCompte}
        />
        <Bascule
          libelle="Résultat"
          valeur={resultat}
          options={ORDRE_RESULTAT.map((id) => ({ id, libelle: LIBELLES_RESULTAT[id] }))}
          onChoisir={setResultat}
        />
        <Bascule
          libelle="Forme"
          valeur={forme}
          options={["toutes", ...formes].map((id) => ({ id, libelle: id === "toutes" ? "Toutes" : id }))}
          onChoisir={setForme}
        />
        <Bascule
          libelle="TVA"
          valeur={tva}
          options={["toutes", ...tvas].map((id) => ({
            id,
            libelle: id === "toutes" ? "Toutes" : libelleTvaRecettes(id),
          }))}
          onChoisir={setTva}
        />
      </div>

      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      {!dossiers && !erreur && <p className="mt-8 text-sm text-subtle">Chargement…</p>}

      <ul className="mt-4">
        {visibles.map((dossier) => (
          <li key={dossier.dossier_id} className="border-b border-hairline">
            <button
              type="button"
              className="flex w-full items-start justify-between gap-8 rounded-lg px-3 py-5 text-left hover:bg-surface-soft"
              onClick={() =>
                setSelection((actuel) => (actuel === dossier.dossier_id ? null : dossier.dossier_id))
              }
            >
              <span className="min-w-0">
                <span className="block truncate text-base font-semibold text-ink">{dossier.nom}</span>
                <span className="mt-1 block text-sm text-subtle">
                  {libelleCompte(dossier.statut_invitation)}
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span
                  className={`block text-lg font-semibold tabular-nums ${
                    dossier.resultat_cts < 0 ? "text-amount-negative" : "text-amount-positive"
                  }`}
                >
                  {formatMontant(dossier.resultat_cts)}
                </span>
                <span className="mt-1 block text-sm tabular-nums text-subtle">
                  CA {formatMontant(dossier.ca_ht_cts)}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {dossiers && visibles.length === 0 && (
        <p className="py-10 text-sm text-subtle">Aucune entreprise pour cette recherche.</p>
      )}

      </div>
      {choisi ? (
        <aside className="flex w-96 shrink-0 flex-col overflow-y-auto border-l border-border bg-canvas p-6">
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-lg font-semibold text-ink">{choisi.nom}</h2>
            <Button type="button" variant="ghost" size="sm" onClick={() => setSelection(null)}>
              Fermer
            </Button>
          </div>
          <p className="mt-1 text-sm text-subtle">{libelleCompte(choisi.statut_invitation)}</p>
          <dl className="mt-6 space-y-4 text-sm">
            <Ligne libelle="Résultat" valeur={formatMontant(choisi.resultat_cts)} />
            <Ligne libelle="CA HT" valeur={formatMontant(choisi.ca_ht_cts)} />
            <Ligne libelle="Charges" valeur={formatMontant(choisi.charges_cts)} />
            <Ligne libelle="Forme" valeur={choisi.forme_juridique} />
            <Ligne libelle="Imposition" valeur={libelleImposition(choisi.regime_imposition)} />
            <Ligne libelle="Régime de TVA" valeur={libelleRegimeTva(choisi.regime_tva)} />
            <Ligne libelle="TVA sur les recettes" valeur={libelleTvaRecettes(choisi.tva_recettes_regime)} />
            <Ligne libelle="Banque" valeur={libelleBanque(choisi.mode_acces_bancaire)} />
            {choisi.plateformes.length > 0 && (
              <Ligne libelle="Plateformes" valeur={choisi.plateformes.join(", ")} />
            )}
            {choisi.exercice_debut && (
              <Ligne
                libelle="Exercice"
                valeur={
                  choisi.exercice_fin
                    ? `${formatDate(choisi.exercice_debut)} au ${formatDate(choisi.exercice_fin)}`
                    : formatDate(choisi.exercice_debut)
                }
              />
            )}
          </dl>
          <div className="mt-8">
            <p className="text-sm font-medium text-ink">Rappels</p>
            {regles.length === 0 && (
              <p className="mt-2 text-sm text-subtle">
                Aucune règle. Elles se préparent dans Rappels.
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {regles.map((regle) => (
                <Button
                  key={regle.id}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={async () => {
                    setInfoRappel(null);
                    try {
                      await declencherRappel(regle.id, choisi.dossier_id);
                      setInfoRappel(`${regle.libelle} enregistré. Envoi prévu quand le canal sera branché.`);
                    } catch (exception) {
                      setInfoRappel(exception instanceof Error ? exception.message : "Échec du rappel.");
                    }
                  }}
                >
                  {regle.libelle}
                </Button>
              ))}
            </div>
            {infoRappel && <p className="mt-2 text-sm text-subtle">{infoRappel}</p>}
          </div>
          <div className="mt-auto flex justify-end pt-8">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-danger"
              onClick={async () => {
                await retirerDossier(choisi.dossier_id);
                setSelection(null);
                charger();
              }}
            >
              Retirer
            </Button>
          </div>
        </aside>
      ) : (
        <nav className="flex w-14 shrink-0 flex-col items-center gap-1 border-l border-border bg-canvas py-3">
          <Raccourci href="/rappels" libelle="Rappels">
            <Bell className="h-4 w-4" />
          </Raccourci>
          <Raccourci href="/invitations" libelle="Invitations">
            <Mail className="h-4 w-4" />
          </Raccourci>
          <Raccourci href="/equipe" libelle="Équipe">
            <Users className="h-4 w-4" />
          </Raccourci>
          <Raccourci href="/integrations" libelle="Intégrations">
            <Plug className="h-4 w-4" />
          </Raccourci>
        </nav>
      )}
    </div>
  );
}

function Total({ libelle, valeur, montant }: { libelle: string; valeur: string; montant?: number }) {
  const couleur =
    montant === undefined ? "text-ink" : montant < 0 ? "text-amount-negative" : "text-amount-positive";
  return (
    <div>
      <dt className="text-sm text-subtle">{libelle}</dt>
      <dd className={`mt-1 text-2xl font-bold tabular-nums tracking-tight ${couleur}`}>{valeur}</dd>
    </div>
  );
}

const ORDRE_COMPTE: FiltreCompte[] = ["tous", "sans_compte", "invite", "ouvert"];
const ORDRE_RESULTAT: FiltreResultat[] = ["tous", "positif", "negatif"];
const LIBELLES_COMPTE: Record<FiltreCompte, string> = {
  tous: "Tous",
  sans_compte: "Sans compte",
  invite: "Invitation envoyée",
  ouvert: "Compte ouvert",
};
const LIBELLES_RESULTAT: Record<FiltreResultat, string> = {
  tous: "Tous",
  positif: "Positif",
  negatif: "Négatif",
};

function Bascule({
  libelle,
  valeur,
  options,
  onChoisir,
}: {
  libelle: string;
  valeur: string;
  options: { id: string; libelle: string }[];
  onChoisir: (id: string) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const maintien = useRef(false);
  const minuteur = useRef<number | null>(null);
  const affiche = options.find((option) => option.id === valeur)?.libelle ?? valeur;

  function relacher() {
    if (minuteur.current !== null) window.clearTimeout(minuteur.current);
  }

  return (
    <span className="relative">
      <button
        type="button"
        onPointerDown={() => {
          maintien.current = false;
          minuteur.current = window.setTimeout(() => {
            maintien.current = true;
            setOuvert(true);
          }, 350);
        }}
        onPointerUp={relacher}
        onPointerLeave={relacher}
        onClick={() => {
          if (maintien.current) {
            maintien.current = false;
            return;
          }
          const index = options.findIndex((option) => option.id === valeur);
          const suivant = options[(index + 1) % options.length];
          if (suivant) onChoisir(suivant.id);
        }}
        className="rounded-full border border-border bg-canvas px-3 py-1.5 text-sm text-ink hover:bg-surface-soft"
      >
        <span className="text-subtle">{libelle}</span>
        <span className="mx-1.5 text-faint">·</span>
        {affiche}
      </button>
      {ouvert && (
        <span className="absolute left-0 z-10 mt-1 flex min-w-40 flex-col rounded-lg border border-border bg-canvas py-1 shadow-sm">
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              className="px-3 py-1.5 text-left text-sm text-ink hover:bg-surface-soft"
              onClick={() => {
                onChoisir(option.id);
                setOuvert(false);
              }}
            >
              {option.libelle}
            </button>
          ))}
        </span>
      )}
    </span>
  );
}

function Raccourci({
  href,
  libelle,
  children,
}: {
  href: string;
  libelle: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      title={libelle}
      aria-label={libelle}
      className="flex h-9 w-9 items-center justify-center rounded-lg text-subtle hover:bg-surface-soft hover:text-ink"
    >
      {children}
    </Link>
  );
}

function Ligne({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-subtle">{libelle}</dt>
      <dd className="text-right text-ink">{valeur}</dd>
    </div>
  );
}
