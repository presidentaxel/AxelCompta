"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/** Si Supabase renvoie le lien vers la racine du site, le fragment
 * `#access_token` est repris vers `/auth/lien`. L'invitation chauffeur
 * a déjà sa page. `location.replace` garde le fragment : le routeur
 * Next le perd. */
export function RebondLienAuth() {
  const chemin = usePathname();

  useEffect(() => {
    if (chemin === "/auth/lien" || chemin.startsWith("/chauffeur/accepter-invitation")) {
      return;
    }
    const fragment = window.location.hash;
    if (fragment.includes("access_token=")) {
      window.location.replace(`/auth/lien${fragment}`);
    }
  }, [chemin]);

  return null;
}
