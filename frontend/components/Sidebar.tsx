"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Bell, FlaskConical, Landmark, LayoutGrid, Plug, Users } from "lucide-react";

import { Marque } from "@/components/Marque";
import { useConnexionsATraiter } from "@/lib/connexions-a-traiter";
import {
  deconnecterGestionnaire,
  estPortefeuilleDemo,
  lireNomPortefeuille,
  obtenirSessionGestionnaire,
  renommerPortefeuille,
} from "@/lib/auth-gestionnaire";

const LIENS = [
  { href: "/portefeuille", libelle: "Entreprises", Icone: LayoutGrid },
  { href: "/connexions-bancaires", libelle: "Connexions bancaires", Icone: Landmark },
  { href: "/rappels", libelle: "Rappels", Icone: Bell },
  { href: "/equipe", libelle: "Équipe", Icone: Users },
  { href: "/integrations", libelle: "Intégrations", Icone: Plug },
];

export function Sidebar() {
  const chemin = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("Organisation");
  const [demo, setDemo] = useState(false);
  const connexionsATraiter = useConnexionsATraiter();

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEmail(obtenirSessionGestionnaire()?.email ?? "");
    setDemo(estPortefeuilleDemo());
    lireNomPortefeuille()
      .then((valeur) => {
        if (valeur) setNom(valeur);
      })
      .catch(() => undefined);
  }, []);

  async function enregistrerNom() {
    const propre = nom.trim();
    if (!propre) return;
    try {
      setNom(await renommerPortefeuille(propre));
    } catch {
      // Le nom saisi reste à l'écran ; un nouvel essai réécrit.
    }
  }

  function seDeconnecter() {
    deconnecterGestionnaire();
    router.push("/connexion");
  }

  return (
    <aside className="flex h-full w-[232px] shrink-0 flex-col border-r border-border bg-canvas-app px-3 py-4">
      <div className="px-2">
        <Marque />
      </div>
      <div className="mb-3 mt-4 flex items-center gap-2.5 border-b border-border px-2 pb-4">
        <span className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-md bg-surface-soft text-[11px] font-medium text-subtle">
          {email.slice(0, 2).toUpperCase() || "AX"}
        </span>
        <span className="min-w-0 flex-1">
          <input
            value={nom}
            onChange={(evenement) => setNom(evenement.target.value)}
            onBlur={enregistrerNom}
            aria-label="Nom de l'organisation"
            className="w-full truncate bg-transparent text-[13.5px] font-medium leading-tight text-ink outline-none"
          />
          <span className="block text-xs text-muted">Organisation</span>
        </span>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5">
        {LIENS.map(({ href, libelle, Icone }) => {
          const actif = chemin === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={actif ? "page" : undefined}
              className={`flex h-[34px] items-center gap-2.5 rounded-md px-2.5 text-[13.5px] font-medium transition-colors duration-150 ${
                actif ? "bg-surface-soft text-ink" : "text-subtle hover:bg-surface-soft hover:text-ink"
              }`}
            >
              <Icone className="h-4 w-4" strokeWidth={1.7} aria-hidden />
              {libelle}
              {href === "/connexions-bancaires" && connexionsATraiter > 0 && (
                <span className="ml-auto flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-medium text-on-primary">
                  {connexionsATraiter}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="mt-4 border-t border-border pt-3 text-[13px]">
        <p className="truncate px-2.5 pb-1.5 text-xs text-muted">{email}</p>
        {demo && (
          <Link
            href="/demo"
            className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 ${
              chemin === "/demo" ? "bg-surface-soft font-medium text-ink" : "text-subtle hover:bg-surface-soft hover:text-ink"
            }`}
          >
            <FlaskConical className="h-4 w-4" strokeWidth={1.7} aria-hidden />
            Démo
          </Link>
        )}
        <Link
          href="/compte"
          className={`block rounded-md px-2.5 py-1.5 ${
            chemin === "/compte" ? "bg-surface-soft font-medium text-ink" : "text-subtle hover:bg-surface-soft hover:text-ink"
          }`}
        >
          Compte
        </Link>
        <button
          type="button"
          onClick={seDeconnecter}
          className="block w-full rounded-md px-2.5 py-1.5 text-left text-subtle hover:bg-surface-soft hover:text-ink"
        >
          Se déconnecter
        </button>
      </div>
    </aside>
  );
}
