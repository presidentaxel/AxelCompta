"use client";

import { useRouter } from "next/navigation";

import { FormulaireConnexion } from "@/components/FormulaireConnexion";
import { connexionParMotDePasse } from "@/lib/auth-chauffeur";

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
        router.push(`/chauffeur/${session.dossierId}`);
      }}
    />
  );
}
