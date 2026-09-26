"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormulaireCompte } from "@/components/FormulaireCompte";
import {
  changerEmailAvecJeton,
  deconnecter,
  definirMotDePasse,
  obtenirSession,
} from "@/lib/auth-chauffeur";

export default function CompteChauffeurPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [jeton, setJeton] = useState<string | null>(null);

  useEffect(() => {
    const session = obtenirSession();
    if (!session) {
      router.replace("/chauffeur/login");
      return;
    }
    // Lecture de localStorage : même pont que le layout chauffeur.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEmail(session.email);
    setJeton(session.accessToken);
  }, [router]);

  if (!email || !jeton) {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }

  return (
    <div>
      <FormulaireCompte
        email={email}
        onMotDePasse={definirMotDePasse}
        onEmail={(adresse) => changerEmailAvecJeton(jeton, adresse)}
      />
      <button
        type="button"
        className="mt-10 text-sm font-medium text-danger"
        onClick={() => {
          deconnecter();
          router.push("/chauffeur/login");
        }}
      >
        Se déconnecter
      </button>
    </div>
  );
}
