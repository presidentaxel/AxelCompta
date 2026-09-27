"use client";

import { useRouter } from "next/navigation";

import { FormulaireConnexion } from "@/components/FormulaireConnexion";
import { connexionParMotDePasse } from "@/lib/auth-chauffeur";
import { cheminDeRetour } from "@/lib/session";

/** doc 19 §5.2 : e-mail + mot de passe, ou lien magique. Pas de
 * self-signup : le lien magique refuse de créer un compte. */
export default function ConnexionChauffeurPage() {
  const router = useRouter();

  return (
    <FormulaireConnexion
      titre="Connexion"
      sousTitre="Retrouvez vos transactions et vos justificatifs."
      onConnecte={async (email, motDePasse) => {
        const session = await connexionParMotDePasse(email, motDePasse);
        // Un retour vers le dossier d'un autre renvoie de toute façon vers le
        // sien (`use-dossier.ts`).
        router.push(cheminDeRetour(window.location.search, `/chauffeur/${session.dossierId}`));
      }}
    />
  );
}
