"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErreurAuthGestionnaire, lirePortefeuilleSession, listerDossiers } from "@/lib/auth-gestionnaire";
import {
  libelleBanque,
  libelleCompte,
  libelleImposition,
  libelleRegimeTva,
  libelleTvaRecettes,
} from "@/lib/dossier-libelles";
import { formatMontant } from "@/lib/format";
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
  const [filtresOuverts, setFiltresOuverts] = useState(false);
  const [selection, setSelection] = useState<string | null>(null);

  const charger = useCallback(() => {
    listerDossiers()
      .then(setDossiers)
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) {
          router.replace("/connexion");
        } else {
          setErreur("Impossible de charger le portefeuille.");
        }
      });
  }, [router]);

  useEffect(() => {
    const memo = lirePortefeuilleSession();
    // Lecture de sessionStorage avant le rafraîchissement réseau.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (memo) setDossiers(memo);
    charger();
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

  const filtresActifs = [compte !== "tous", resultat !== "tous", forme !== "toutes", tva !== "toutes"].filter(
    Boolean,
  ).length;
  const choisi = dossiers?.find((dossier) => dossier.dossier_id === selection) ?? null;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Portefeuille</h1>
      {dossiers && (
        <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-4">
          <Total libelle="Chauffeurs" valeur={String(totaux.nombre)} />
          <Total libelle="Sans compte" valeur={String(totaux.sansCompte)} />
          <Total libelle="Résultat" valeur={formatMontant(totaux.resultat)} montant={totaux.resultat} />
        </dl>
      )}

      <div className="mt-8 flex items-center gap-2">
        <Input
          value={recherche}
          onChange={(evenement) => setRecherche(evenement.target.value)}
          placeholder="Rechercher un chauffeur"
          aria-label="Rechercher un chauffeur"
        />
        <Button type="button" variant="secondary" onClick={() => setFiltresOuverts((ouvert) => !ouvert)}>
          Filtres{filtresActifs > 0 ? ` (${filtresActifs})` : ""}
        </Button>
      </div>
      {filtresOuverts && (
        <div className="mt-3 rounded-lg border border-border bg-canvas p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Choix
              libelle="Compte"
              valeur={compte}
              onChange={setCompte}
              options={[
                ["tous", "Tous"],
                ["sans_compte", "Sans compte"],
                ["invite", "Invitation envoyée"],
                ["ouvert", "Compte ouvert"],
              ]}
            />
            <Choix
              libelle="Résultat"
              valeur={resultat}
              onChange={setResultat}
              options={[
                ["tous", "Tous"],
                ["positif", "Positif"],
                ["negatif", "Négatif"],
              ]}
            />
            <Choix
              libelle="Forme"
              valeur={forme}
              onChange={setForme}
              options={[["toutes", "Toutes"], ...formes.map((valeur) => [valeur, valeur] as [string, string])]}
            />
            <Choix
              libelle="TVA sur les recettes"
              valeur={tva}
              onChange={setTva}
              options={[
                ["toutes", "Toutes"],
                ...tvas.map((valeur) => [valeur, libelleTvaRecettes(valeur)] as [string, string]),
              ]}
            />
          </div>
          {filtresActifs > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-3"
              onClick={() => {
                setCompte("tous");
                setResultat("tous");
                setForme("toutes");
                setTva("toutes");
              }}
            >
              Effacer
            </Button>
          )}
        </div>
      )}

      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      {!dossiers && !erreur && <p className="mt-8 text-sm text-subtle">Chargement…</p>}

      <ul className="mt-4">
        {visibles.map((dossier) => (
          <li key={dossier.dossier_id} className="border-b border-hairline">
            <button
              type="button"
              className="flex w-full items-start justify-between gap-8 py-5 text-left hover:bg-surface-soft"
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
        <p className="py-10 text-sm text-subtle">Aucun chauffeur pour cette recherche.</p>
      )}

      {choisi && (
        <aside className="fixed inset-y-0 right-0 z-20 w-full max-w-sm overflow-y-auto border-l border-border bg-canvas p-6 shadow-lg">
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
                    ? `${choisi.exercice_debut} au ${choisi.exercice_fin}`
                    : choisi.exercice_debut
                }
              />
            )}
          </dl>
        </aside>
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

function Choix<T extends string>({
  libelle,
  valeur,
  onChange,
  options,
}: {
  libelle: string;
  valeur: T;
  onChange: (valeur: T) => void;
  options: [T, string][];
}) {
  return (
    <label className="block text-sm">
      <span className="font-medium text-ink">{libelle}</span>
      <select
        value={valeur}
        onChange={(evenement) => onChange(evenement.target.value as T)}
        className="mt-1 h-9 w-full rounded-md border border-border bg-canvas px-3 text-sm text-ink outline-none focus-visible:border-border-focus"
      >
        {options.map(([id, texte]) => (
          <option key={id} value={id}>
            {texte}
          </option>
        ))}
      </select>
    </label>
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
