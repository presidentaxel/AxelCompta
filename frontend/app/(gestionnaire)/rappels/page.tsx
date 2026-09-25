"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  creerRegle,
  ErreurAuthGestionnaire,
  listerRegles,
  type RegleRappel,
} from "@/lib/auth-gestionnaire";

const CANAUX = [
  { id: "sms", libelle: "SMS" },
  { id: "mail", libelle: "E-mail" },
  { id: "appel", libelle: "Appel" },
];

/** Réglages des rappels. Les boutons qui en découlent sont sur la fiche.
 * SMS, e-mail et appel (Volubile) s'enverront quand le canal sera branché. */
export default function RappelsPage() {
  const router = useRouter();
  const [regles, setRegles] = useState<RegleRappel[] | null>(null);
  const [libelle, setLibelle] = useState("");
  const [message, setMessage] = useState("");
  const [canaux, setCanaux] = useState<string[]>(["sms"]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    listerRegles()
      .then(setRegles)
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) {
          router.replace("/connexion");
        } else {
          setErreur("Impossible de charger les rappels.");
        }
      });
  }, [router]);

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Rappels</h1>
      <p className="mt-2 text-sm text-subtle">
        Chaque règle devient un bouton sur la fiche. Coche SMS, e-mail ou appel. L&apos;envoi
        partira quand le canal sera branché.
      </p>
      <form
        className="mt-8 space-y-3"
        onSubmit={async (evenement) => {
          evenement.preventDefault();
          setEnCours(true);
          setErreur(null);
          try {
            await creerRegle(libelle.trim(), message.trim(), canaux);
            setLibelle("");
            setMessage("");
            setRegles(await listerRegles());
          } catch (exception) {
            setErreur(exception instanceof Error ? exception.message : "Échec de l'enregistrement.");
          } finally {
            setEnCours(false);
          }
        }}
      >
        <Input
          value={libelle}
          onChange={(evenement) => setLibelle(evenement.target.value)}
          placeholder="Nom du bouton, par exemple Pièces à jour"
          required
          disabled={enCours}
        />
        <Input
          value={message}
          onChange={(evenement) => setMessage(evenement.target.value)}
          placeholder="Message envoyé"
          required
          disabled={enCours}
        />
        <div className="flex gap-2">
          {CANAUX.map((canal) => {
            const actif = canaux.includes(canal.id);
            return (
              <button
                key={canal.id}
                type="button"
                onClick={() =>
                  setCanaux((actuel) =>
                    actif ? actuel.filter((id) => id !== canal.id) : [...actuel, canal.id],
                  )
                }
                className={`rounded-full border px-3 py-1.5 text-sm ${
                  actif ? "border-primary bg-primary-subtle text-primary" : "border-border text-subtle"
                }`}
              >
                {canal.libelle}
              </button>
            );
          })}
        </div>
        <Button type="submit" disabled={enCours || canaux.length === 0}>
          Ajouter la règle
        </Button>
      </form>
      {erreur && <p className="mt-4 text-sm text-danger">{erreur}</p>}
      <ul className="mt-8">
        {regles?.map((regle) => (
          <li key={regle.id} className="border-b border-hairline py-4">
            <p className="text-sm font-medium text-ink">{regle.libelle}</p>
            <p className="mt-1 text-sm text-subtle">{regle.message}</p>
            <p className="mt-1 text-xs text-subtle">{regle.canaux.join(", ")}</p>
          </li>
        ))}
      </ul>
      {regles && regles.length === 0 && <p className="mt-8 text-sm text-subtle">Aucune règle.</p>}
    </div>
  );
}
