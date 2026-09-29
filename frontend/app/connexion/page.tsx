"use client";

import { useRouter } from "next/navigation";

import { FormulaireConnexion } from "@/components/FormulaireConnexion";
import { connexionGestionnaire } from "@/lib/auth-gestionnaire";
import { cheminDeRetour } from "@/lib/session";

/** Connexion gestionnaire (doc 03 §7). Hors du groupe `(gestionnaire)` pour
 * ne pas hériter de la Sidebar/TopBar avant d'être connecté. */
export default function ConnexionGestionnairePage() {
  const router = useRouter();

  return (
    <div className="theme-pro min-h-screen">
      <main className="mx-auto max-w-sm px-4 pt-24">
        <FormulaireConnexion
          titre="Connexion gestionnaire"
          sousTitre="Accédez à l'état de votre portefeuille."
          onConnecte={async (email, motDePasse) => {
            await connexionGestionnaire(email, motDePasse);
            router.push(cheminDeRetour(window.location.search, "/"));
          }}
        />
      </main>
    </div>
  );
}
