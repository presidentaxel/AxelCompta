"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pastille } from "@/components/Pastille";
import { Segments } from "@/components/Segments";
import {
  creerRegle,
  ErreurAuthGestionnaire,
  listerDossiers,
  listerRegles,
  type RegleRappel,
} from "@/lib/auth-gestionnaire";
import type { DossierAgregat } from "@/lib/types";

const CANAUX = [
  { id: "sms", libelle: "SMS" },
  { id: "mail", libelle: "E-mail" },
  { id: "appel", libelle: "Appel" },
];

const PREFAITS: {
  libelle: string;
  message: string;
  canaux: string[];
  declencheur: string;
  jours_avant: number | null;
}[] = [
  {
    libelle: "15 jours avant la clôture",
    message: "La clôture approche. Relis les pièces de l'exercice.",
    canaux: ["mail"],
    declencheur: "avant_cloture",
    jours_avant: 15,
  },
  {
    libelle: "Compte à ouvrir",
    message: "Ouvre ton compte pour suivre l'exercice.",
    canaux: ["mail", "sms"],
    declencheur: "manuel",
    jours_avant: null,
  },
  {
    libelle: "Pièces à compléter",
    message: "Il reste des pièces à ajouter avant la clôture.",
    canaux: ["sms"],
    declencheur: "manuel",
    jours_avant: null,
  },
];

/** Réglages. Une règle « avant clôture » part seule pour les entreprises
 * concernées. L'envoi réel attend le branchement du canal. */
export default function RappelsPage() {
  const router = useRouter();
  const [regles, setRegles] = useState<RegleRappel[] | null>(null);
  const [dossiers, setDossiers] = useState<DossierAgregat[]>([]);
  const [libelle, setLibelle] = useState("");
  const [message, setMessage] = useState("");
  const [canaux, setCanaux] = useState<string[]>(["mail"]);
  const [declencheur, setDeclencheur] = useState("avant_cloture");
  const [jours, setJours] = useState("15");
  const [portee, setPortee] = useState("tous");
  const [choisis, setChoisis] = useState<string[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  // Le mode strict de React lance l'effet deux fois en développement : sans
  // garde, chaque passe voit les règles de base « manquantes » et les crée.
  const initialise = useRef(false);

  useEffect(() => {
    if (initialise.current) return;
    initialise.current = true;
    listerRegles()
      .then(async (liste) => {
        const manquantes = PREFAITS.filter(
          (modele) => !liste.some((regle) => regle.libelle === modele.libelle),
        );
        // Seul un admin crée les règles préfaites ; un membre ou une
        // lecture voit la liste telle quelle.
        for (const modele of manquantes) {
          await creerRegle({ ...modele, portee: "tous" }).catch(() => undefined);
        }
        setRegles(manquantes.length > 0 ? await listerRegles() : liste);
      })
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) router.replace("/connexion");
        else setErreur("Impossible de charger les rappels.");
      });
    listerDossiers()
      .then(setDossiers)
      .catch(() => undefined);
  }, [router]);

  async function ajouter(regle: {
    libelle: string;
    message: string;
    canaux: string[];
    declencheur: string;
    jours_avant: number | null;
    portee?: string;
    dossier_ids?: string[];
  }) {
    setEnCours(true);
    setErreur(null);
    try {
      await creerRegle(regle);
      setRegles(await listerRegles());
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Échec de l'enregistrement.");
    } finally {
      setEnCours(false);
    }
  }

  const styleCanal = (actif: boolean) =>
    `h-[30px] rounded-md border px-3 text-[13px] font-medium transition-colors duration-150 ${
      actif ? "border-ink bg-ink text-on-primary" : "border-border-strong text-subtle hover:border-ink hover:text-ink"
    }`;

  return (
    <div className="mx-auto max-w-[1100px]">
      <h1 className="text-[22px] font-medium tracking-tight text-ink">Rappels</h1>
      <p className="mt-1 text-[13.5px] text-subtle">
        Les trois règles de base sont déjà en place. Un rappel part par SMS, e-mail ou appel.
      </p>

      <div className="mt-7 grid items-start gap-10 lg:grid-cols-[1fr_340px]">
        <div>
          {erreur && <p className="mb-4 text-sm text-danger">{erreur}</p>}
          <h2 className="text-[15px] font-medium text-ink">Règles</h2>
          <ul className="mt-1">
            {regles?.map((regle) => (
              <li key={regle.id} className="flex items-start gap-4 border-b border-hairline py-3.5">
                <span className="min-w-0 flex-1">
                  <span className="block text-[13.5px] font-medium text-ink">{regle.libelle}</span>
                  <span className="mt-0.5 block text-[13px] text-subtle">{regle.message}</span>
                  <span className="mt-1 block text-xs text-muted">
                    {regle.declencheur === "avant_cloture"
                      ? `${regle.jours_avant} jours avant la clôture`
                      : "Bouton sur la fiche"}
                    {" - "}
                    {regle.portee === "selection" ? `${regle.dossier_ids.length} entreprise(s)` : "Toutes"}
                  </span>
                </span>
                <span className="flex shrink-0 gap-1.5">
                  {regle.canaux.map((canal) => (
                    <Pastille key={canal} ton="neutre">
                      {CANAUX.find((c) => c.id === canal)?.libelle ?? canal}
                    </Pastille>
                  ))}
                </span>
              </li>
            ))}
          </ul>
          {regles && regles.length === 0 && <p className="mt-3 text-sm text-subtle">Aucune règle.</p>}
          <p className="mt-3 text-xs text-muted">
            Une règle se déclenche à la main depuis la fiche d&apos;une entreprise, ou toute seule avant la
            clôture. L&apos;envoi réel attend le branchement du canal.
          </p>
        </div>

        <form
          className="rounded-[10px] border border-border bg-canvas p-5"
          onSubmit={(evenement) => {
            evenement.preventDefault();
            void ajouter({
              libelle: libelle.trim(),
              message: message.trim(),
              canaux,
              declencheur,
              jours_avant: declencheur === "avant_cloture" ? Number(jours) : null,
              portee,
              dossier_ids: choisis,
            });
            setLibelle("");
            setMessage("");
          }}
        >
          <h2 className="text-[15px] font-medium text-ink">Nouvelle règle</h2>
          <p className="mb-4 mt-0.5 text-xs text-muted">Se crée ici, se déclenche depuis la fiche.</p>
          <div className="space-y-2">
            <Input value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="Nom" required disabled={enCours} />
            <Input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Message" required disabled={enCours} />
          </div>
          <p className="mb-1.5 mt-4 text-xs text-muted">Canaux</p>
          <div className="flex flex-wrap gap-1.5">
            {CANAUX.map((canal) => {
              const actif = canaux.includes(canal.id);
              return (
                <button
                  key={canal.id}
                  type="button"
                  aria-pressed={actif}
                  onClick={() =>
                    setCanaux((actuel) => (actif ? actuel.filter((id) => id !== canal.id) : [...actuel, canal.id]))
                  }
                  className={styleCanal(actif)}
                >
                  {canal.libelle}
                </button>
              );
            })}
          </div>
          <p className="mb-1.5 mt-4 text-xs text-muted">Déclenchement</p>
          <Segments
            label="Déclenchement"
            valeur={declencheur}
            onChange={setDeclencheur}
            options={[
              { valeur: "avant_cloture", libelle: "Avant la clôture" },
              { valeur: "manuel", libelle: "Bouton sur la fiche" },
            ]}
          />
          {declencheur === "avant_cloture" && (
            <label className="mt-2 flex items-center gap-2 text-[13px] text-subtle">
              <Input
                value={jours}
                onChange={(e) => setJours(e.target.value)}
                inputMode="numeric"
                className="w-16"
                aria-label="Jours avant la clôture"
              />
              jours avant
            </label>
          )}
          <p className="mb-1.5 mt-4 text-xs text-muted">Entreprises</p>
          <Segments
            label="Entreprises concernées"
            valeur={portee}
            onChange={setPortee}
            options={[
              { valeur: "tous", libelle: "Toutes" },
              { valeur: "selection", libelle: "Certaines" },
            ]}
          />
          {portee === "selection" && (
            <ul className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-border">
              {dossiers.map((dossier) => (
                <li key={dossier.dossier_id}>
                  <label className="flex items-center gap-2 px-3 py-2 text-[13px] text-ink">
                    <input
                      type="checkbox"
                      checked={choisis.includes(dossier.dossier_id)}
                      onChange={() =>
                        setChoisis((actuel) =>
                          actuel.includes(dossier.dossier_id)
                            ? actuel.filter((id) => id !== dossier.dossier_id)
                            : [...actuel, dossier.dossier_id],
                        )
                      }
                    />
                    {dossier.nom}
                  </label>
                </li>
              ))}
            </ul>
          )}
          <Button type="submit" className="mt-5 w-full" disabled={enCours || canaux.length === 0}>
            Enregistrer la règle
          </Button>
        </form>
      </div>
    </div>
  );
}
