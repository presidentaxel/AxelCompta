"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FriseDetaillee, MiniFrise } from "@/components/FriseEntreprise";
import { Pastille } from "@/components/Pastille";
import { Selecteur } from "@/components/Selecteur";
import {
  declencherRappel,
  ErreurAuthGestionnaire,
  lirePortefeuilleSession,
  listerDossiers,
  listerRegles,
  retirerDossier,
  type RegleRappel,
} from "@/lib/auth-gestionnaire";
import { useConnexionsATraiter } from "@/lib/connexions-a-traiter";
import {
  libelleBanque,
  libelleImposition,
  libelleRegimeTva,
  libelleTvaRecettes,
} from "@/lib/dossier-libelles";
import { formatDate, formatMontant } from "@/lib/format";
import type { DossierAgregat } from "@/lib/types";

type FiltreCompte = "tous" | "sans_compte" | "invite" | "ouvert";
type FiltreResultat = "tous" | "negatif" | "positif";

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

/** Entreprises : une table, une ligne par entreprise. Une ligne se déplie sur
 * place pour montrer la frise détaillée, la fiche et les actions : une seule
 * ligne ouverte à la fois, pas de panneau à côté. */
export default function PortefeuillePage() {
  const router = useRouter();
  const [dossiers, setDossiers] = useState<DossierAgregat[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");
  const [compte, setCompte] = useState<FiltreCompte>("tous");
  const [resultat, setResultat] = useState<FiltreResultat>("tous");
  const [forme, setForme] = useState("toutes");
  const [tva, setTva] = useState("toutes");
  const [ouvert, setOuvert] = useState<string | null>(null);
  const [regles, setRegles] = useState<RegleRappel[]>([]);

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

  // Une ligne ouverte puis exclue par un filtre ne réapparaît pas dépliée.
  const ouverte = visibles.some((dossier) => dossier.dossier_id === ouvert) ? ouvert : null;

  const totaux = useMemo(() => {
    const liste = dossiers ?? [];
    return {
      nombre: liste.length,
      sansCompte: liste.filter((dossier) => dossier.statut_invitation === null).length,
      resultat: liste.reduce((somme, dossier) => somme + dossier.resultat_cts, 0),
    };
  }, [dossiers]);

  return (
    <div className="mx-auto max-w-[1100px]">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[22px] font-medium tracking-tight text-ink">Entreprises</h1>
          {dossiers && (
            <p className="mt-1 text-[13.5px] text-subtle">
              {visibles.length === totaux.nombre
                ? `${totaux.nombre} ${totaux.nombre > 1 ? "entreprises" : "entreprise"}`
                : `${visibles.length} affichées sur ${totaux.nombre}`}
            </p>
          )}
        </div>
        <Button asChild variant="secondary">
          <Link href="/invitations">Invitations</Link>
        </Button>
      </div>
      <AlerteConnexions />
      {dossiers && (
        <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-3">
          <Total libelle="Entreprises" valeur={String(totaux.nombre)} />
          <Total libelle="Sans compte" valeur={String(totaux.sansCompte)} />
          <Total
            libelle="Résultat cumulé"
            valeur={formatMontant(totaux.resultat)}
            montant={totaux.resultat}
          />
        </dl>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Input
          value={recherche}
          onChange={(evenement) => setRecherche(evenement.target.value)}
          placeholder="Rechercher une entreprise"
          aria-label="Rechercher une entreprise"
          className="w-64"
        />
        <Selecteur
          libelle="Compte"
          valeur={compte}
          options={ORDRE_COMPTE.map((id) => ({ id, libelle: LIBELLES_COMPTE[id] }))}
          onChoisir={setCompte}
        />
        <Selecteur
          libelle="Résultat"
          valeur={resultat}
          options={ORDRE_RESULTAT.map((id) => ({ id, libelle: LIBELLES_RESULTAT[id] }))}
          onChoisir={setResultat}
        />
        <Selecteur
          libelle="Forme"
          valeur={forme}
          options={["toutes", ...formes].map((id) => ({ id, libelle: id === "toutes" ? "Toutes" : id }))}
          onChoisir={setForme}
        />
        <Selecteur
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

      {dossiers && visibles.length > 0 && (
        <table className="mt-5 w-full border-collapse text-[13.5px]">
          <thead>
            <tr className="border-b border-border text-left text-[11.5px] font-medium tracking-wide text-muted">
              <th className="w-8 pb-2">
                <span className="sr-only">Détail</span>
              </th>
              <th className="w-[26%] pb-2 pr-3">Entreprise</th>
              <th className="w-[19%] pb-2 pr-3">Compte</th>
              <th className="pb-2 pr-3">Avancement</th>
              <th className="w-[14%] pb-2 text-right">Résultat</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((dossier) => (
              <LigneEntreprise
                key={dossier.dossier_id}
                dossier={dossier}
                ouvert={ouverte === dossier.dossier_id}
                regles={regles}
                onBasculer={() =>
                  setOuvert(ouverte === dossier.dossier_id ? null : dossier.dossier_id)
                }
                onRetire={() => {
                  setOuvert(null);
                  charger();
                }}
              />
            ))}
          </tbody>
        </table>
      )}
      {dossiers && visibles.length === 0 && (
        <p className="py-10 text-sm text-subtle">Aucune entreprise pour cette recherche.</p>
      )}
    </div>
  );
}

function Total({ libelle, valeur, montant }: { libelle: string; valeur: string; montant?: number }) {
  const couleur =
    montant === undefined ? "text-ink" : montant < 0 ? "text-amount-negative" : "text-amount-positive";
  return (
    <div>
      <dt className="text-xs text-muted">{libelle}</dt>
      <dd className={`mt-0.5 text-[22px] font-normal tabular-nums tracking-tight ${couleur}`}>{valeur}</dd>
    </div>
  );
}

function LigneEntreprise({
  dossier,
  ouvert,
  regles,
  onBasculer,
  onRetire,
}: {
  dossier: DossierAgregat;
  ouvert: boolean;
  regles: RegleRappel[];
  onBasculer: () => void;
  onRetire: () => void;
}) {
  const compteOuvert = dossier.statut_invitation === "actif";
  return (
    <>
      <tr
        onClick={onBasculer}
        className={`cursor-pointer border-b border-hairline transition-colors duration-100 hover:bg-surface-soft ${
          ouvert ? "border-b-0 bg-canvas" : ""
        }`}
      >
        <td className="py-3 pl-1">
          <button
            type="button"
            aria-expanded={ouvert}
            aria-label={`${ouvert ? "Replier" : "Déplier"} ${dossier.nom}`}
            onClick={(evenement) => {
              evenement.stopPropagation();
              onBasculer();
            }}
            className="flex h-6 w-6 items-center justify-center rounded-md text-muted hover:text-ink"
          >
            <ChevronRight
              className={`h-4 w-4 transition-transform duration-150 ${ouvert ? "rotate-90 text-ink" : ""}`}
              aria-hidden
            />
          </button>
        </td>
        <td className="py-3 pr-3">
          <span className="block font-medium text-ink">{dossier.nom}</span>
          <span className="mt-0.5 block text-xs text-muted">
            {dossier.forme_juridique} - {libelleImpositionCourt(dossier.regime_imposition)}
          </span>
        </td>
        <td className="py-3 pr-3">
          {dossier.statut_invitation === "actif" ? (
            <Pastille ton="positif" point>
              Ouvert
            </Pastille>
          ) : dossier.statut_invitation === "invité" ? (
            <Pastille ton="attention" point>
              Invitation envoyée
            </Pastille>
          ) : (
            <Pastille ton="absent">Sans compte</Pastille>
          )}
        </td>
        <td className="py-3 pr-3">
          {ouvert ? (
            <span className="text-xs text-muted">Frise détaillée ci-dessous</span>
          ) : (
            <span className="block space-y-1.5">
              <MiniFrise
                annee={dossier.annee_courante}
                etape={dossier.etape_courante}
                compteOuvert={compteOuvert}
              />
              <MiniFrise
                annee={dossier.annee_precedente}
                etape={dossier.etape_precedente}
                compteOuvert={compteOuvert}
              />
            </span>
          )}
        </td>
        <td
          className={`py-3 text-right font-medium tabular-nums ${
            dossier.resultat_cts < 0 ? "text-amount-negative" : "text-amount-positive"
          }`}
        >
          {formatMontant(dossier.resultat_cts)}
        </td>
      </tr>
      {ouvert && <FicheEntreprise dossier={dossier} regles={regles} onRetire={onRetire} />}
    </>
  );
}

function libelleImpositionCourt(code: string): string {
  return code === "IS" ? "IS" : code === "option_IR" ? "IR" : libelleImposition(code);
}

/** Contenu de la ligne dépliée : frise détaillée, fiche, rappels, retrait. */
function FicheEntreprise({
  dossier,
  regles,
  onRetire,
}: {
  dossier: DossierAgregat;
  regles: RegleRappel[];
  onRetire: () => void;
}) {
  const [infoRappel, setInfoRappel] = useState<string | null>(null);
  const [confirmerRetrait, setConfirmerRetrait] = useState(false);
  const compteOuvert = dossier.statut_invitation === "actif";
  const alertes = [dossier.alerte_regime, dossier.alerte_tva].filter(
    (alerte): alerte is string => alerte !== null,
  );

  return (
    <tr className="border-b border-hairline bg-canvas">
      <td />
      <td colSpan={4} className="pb-5 pr-1">
        <div className="space-y-3">
          <FriseDetaillee
            annee={dossier.annee_courante}
            etape={dossier.etape_courante}
            compteOuvert={compteOuvert}
          />
          <FriseDetaillee
            annee={dossier.annee_precedente}
            etape={dossier.etape_precedente}
            compteOuvert={compteOuvert}
          />
        </div>
        {alertes.map((alerte) => (
          <p key={alerte} className="mt-3 text-[13px] text-subtle">
            {alerte}
          </p>
        ))}
        <dl className="mt-5 grid grid-cols-2 gap-x-10 border-t border-hairline pt-1 text-[13.5px]">
          <div>
            <Ligne libelle="Résultat" valeur={formatMontant(dossier.resultat_cts)} />
            <Ligne libelle="Chiffre d'affaires HT" valeur={formatMontant(dossier.ca_ht_cts)} />
            <Ligne libelle="Charges" valeur={formatMontant(dossier.charges_cts)} />
            {dossier.exercice_debut && (
              <Ligne
                libelle="Exercice"
                valeur={
                  dossier.exercice_fin
                    ? `${formatDate(dossier.exercice_debut)} au ${formatDate(dossier.exercice_fin)}`
                    : formatDate(dossier.exercice_debut)
                }
              />
            )}
          </div>
          <div>
            <Ligne libelle="Forme" valeur={dossier.forme_juridique} />
            <Ligne libelle="Imposition" valeur={libelleImposition(dossier.regime_imposition)} />
            <Ligne libelle="Régime de TVA" valeur={libelleRegimeTva(dossier.regime_tva)} />
            <Ligne libelle="TVA sur les recettes" valeur={libelleTvaRecettes(dossier.tva_recettes_regime)} />
            <Ligne libelle="Banque" valeur={libelleBanque(dossier.mode_acces_bancaire)} />
            {dossier.plateformes.length > 0 && (
              <Ligne libelle="Plateformes" valeur={dossier.plateformes.join(", ")} />
            )}
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-xs text-muted">Rappels</span>
          {regles.length === 0 && (
            <span className="text-[13px] text-subtle">Aucune règle. Elles se préparent dans Rappels.</span>
          )}
          {regles
            .filter(
              (regle) => regle.portee !== "selection" || regle.dossier_ids.includes(dossier.dossier_id),
            )
            .map((regle) => (
              <Button
                key={regle.id}
                type="button"
                variant="secondary"
                size="sm"
                onClick={async () => {
                  setInfoRappel(null);
                  try {
                    await declencherRappel(regle.id, dossier.dossier_id);
                    setInfoRappel(`${regle.libelle} enregistré. Envoi prévu quand le canal sera branché.`);
                  } catch (exception) {
                    setInfoRappel(exception instanceof Error ? exception.message : "Échec du rappel.");
                  }
                }}
              >
                {regle.libelle}
              </Button>
            ))}
          <span className="flex-1" />
          {confirmerRetrait ? (
            <>
              <span className="text-[13px] text-ink">Retirer {dossier.nom} de la liste ?</span>
              <Button type="button" variant="ghost" size="sm" onClick={() => setConfirmerRetrait(false)}>
                Annuler
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={async () => {
                  await retirerDossier(dossier.dossier_id);
                  setConfirmerRetrait(false);
                  onRetire();
                }}
              >
                Retirer
              </Button>
            </>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-danger"
              onClick={() => setConfirmerRetrait(true)}
            >
              Retirer de la liste
            </Button>
          )}
        </div>
        {infoRappel && <p className="mt-2 text-[13px] text-subtle">{infoRappel}</p>}
      </td>
    </tr>
  );
}

function Ligne({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-hairline py-2 last:border-b-0">
      <dt className="text-muted">{libelle}</dt>
      <dd className="text-right tabular-nums text-ink">{valeur}</dd>
    </div>
  );
}

/** doc 14 §2.2 : les connexions qui demandent une action se voient dès
 * l'arrivée, sans aller les chercher. */
function AlerteConnexions() {
  const nombre = useConnexionsATraiter();
  if (nombre === 0) return null;
  return (
    <Link
      href="/connexions-bancaires"
      className="mt-5 flex items-center gap-2.5 rounded-md border border-[#f0ddb8] bg-pending-subtle px-3.5 py-2.5 text-[13.5px] text-ink hover:border-warning"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-warning" aria-hidden />
      {nombre === 1
        ? "Une connexion bancaire expire ou doit être confirmée."
        : `${nombre} connexions bancaires expirent ou doivent être confirmées.`}
      <span className="ml-auto font-medium text-primary">Voir</span>
    </Link>
  );
}
