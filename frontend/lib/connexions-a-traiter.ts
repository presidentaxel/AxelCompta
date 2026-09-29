"use client";

import { useEffect, useState } from "react";

import { lireConnexionsBancaires } from "@/lib/auth-gestionnaire";

/** Nombre de connexions bancaires qui demandent une action (expirées, à
 * renouveler ou à confirmer). Une erreur de lecture laisse le compteur à 0
 * plutôt que de gêner l'écran (doc 14 §2.2). */
export function useConnexionsATraiter(): number {
  const [nombre, setNombre] = useState(0);
  useEffect(() => {
    lireConnexionsBancaires()
      .then((donnees) =>
        setNombre(
          donnees.dossiers.filter(
            (dossier) =>
              dossier.statut === "expire" ||
              dossier.statut === "a_renouveler" ||
              dossier.sante === "auth_requise",
          ).length,
        ),
      )
      .catch(() => undefined);
  }, []);
  return nombre;
}
