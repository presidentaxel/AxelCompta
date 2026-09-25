"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { estLienInvitation } from "@/lib/auth-lien";

/** Si Supabase renvoie le lien vers la racine du site, le fragment
 * `#access_token` est repris vers `/auth/lien`. Une invitation
 * (`type=invite`) va sur la page qui demande le mot de passe.
 * `location.replace` garde le fragment : le routeur Next le perd. */
export function RebondLienAuth() {
  const chemin = usePathname();

  useEffect(() => {
    if (chemin === "/auth/lien" || chemin.startsWith("/chauffeur/accepter-invitation")) {
      return;
    }
    const fragment = window.location.hash;
    if (!fragment.includes("access_token=")) {
      return;
    }
    const cible = estLienInvitation(fragment)
      ? `/chauffeur/accepter-invitation${fragment}`
      : `/auth/lien${fragment}`;
    window.location.replace(cible);
  }, [chemin]);

  return null;
}
