"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormulaireCompte } from "@/components/FormulaireCompte";
import {
  changerEmailGestionnaire,
  changerMotDePasseGestionnaire,
  obtenirSessionGestionnaire,
} from "@/lib/auth-gestionnaire";

export default function CompteGestionnairePage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const session = obtenirSessionGestionnaire();
    if (!session) {
      router.replace("/connexion");
      return;
    }
    // Lecture de localStorage : même pont que le layout chauffeur.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEmail(session.email);
  }, [router]);

  if (!email) {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }

  return (
    <div className="mx-auto max-w-sm">
      <FormulaireCompte
        email={email}
        onMotDePasse={changerMotDePasseGestionnaire}
        onEmail={changerEmailGestionnaire}
      />
    </div>
  );
}
