"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ErreurAuthGestionnaire,
  listerMembres,
  obtenirSessionGestionnaire,
  type MembrePortefeuille,
} from "@/lib/auth-gestionnaire";

/** Les gestionnaires d'un même portefeuille voient les mêmes chauffeurs.
 * L'accès est le même pour tous : agrégats et invitations. */
export default function EquipePage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [membres, setMembres] = useState<MembrePortefeuille[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const session = obtenirSessionGestionnaire();
    if (!session) {
      router.replace("/connexion");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEmail(session.email);
    listerMembres()
      .then(setMembres)
      .catch((exception) => {
        if (exception instanceof ErreurAuthGestionnaire) {
          router.replace("/connexion");
        } else {
          setErreur("Impossible de charger l'équipe.");
        }
      });
  }, [router]);

  const liste =
    membres && membres.length > 0
      ? membres
      : email
        ? [{ email, acces: "portefeuille" }]
        : [];

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Équipe</h1>
      <p className="mt-2 text-sm text-subtle">
        Ces comptes voient le même portefeuille. Chacun peut consulter les agrégats et envoyer des
        invitations. Le détail des écritures reste côté chauffeur.
      </p>
      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      <ul className="mt-8">
        {liste.map((membre) => (
          <li
            key={membre.email}
            className="flex items-center justify-between border-b border-hairline py-4"
          >
            <span className="text-sm font-medium text-ink">
              {membre.email}
              {membre.email === email ? " (vous)" : ""}
            </span>
            <span className="text-sm text-subtle">Portefeuille</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
