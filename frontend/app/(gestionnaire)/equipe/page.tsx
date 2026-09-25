"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  changerRole,
  ErreurAuthGestionnaire,
  inviterMembre,
  listerMembres,
  obtenirSessionGestionnaire,
  type MembrePortefeuille,
  type RoleMembre,
} from "@/lib/auth-gestionnaire";

const ROLES: { id: RoleMembre; libelle: string }[] = [
  { id: "admin", libelle: "Admin" },
  { id: "membre", libelle: "Membre" },
  { id: "lecture", libelle: "Lecture" },
];

/** Admin : nom, équipe, retraits, règles. Membre : invitations et rappels.
 * Lecture : consultation. Un compte déjà là sans ligne est admin. */
export default function EquipePage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [membres, setMembres] = useState<MembrePortefeuille[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [emailInvite, setEmailInvite] = useState("");
  const [roleInvite, setRoleInvite] = useState<RoleMembre>("membre");
  const [enCours, setEnCours] = useState(false);

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
    membres && membres.length > 0 ? membres : email ? [{ email, role: "admin" as const }] : [];

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Équipe</h1>
      <p className="mt-2 text-sm text-subtle">
        Admin gère le nom, l&apos;équipe, les retraits et les règles. Membre invite et envoie des
        rappels. Lecture consulte seulement.
      </p>
      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}
      <form
        className="mt-8 flex flex-wrap items-center gap-2"
        onSubmit={async (evenement) => {
          evenement.preventDefault();
          setEnCours(true);
          setErreur(null);
          try {
            await inviterMembre(emailInvite.trim(), roleInvite);
            setEmailInvite("");
            setMembres(await listerMembres());
          } catch (exception) {
            setErreur(exception instanceof Error ? exception.message : "Échec de l'invitation.");
          } finally {
            setEnCours(false);
          }
        }}
      >
        <Input
          type="email"
          required
          value={emailInvite}
          onChange={(evenement) => setEmailInvite(evenement.target.value)}
          placeholder="E-mail du collègue"
          disabled={enCours}
          className="max-w-xs"
        />
        <select
          value={roleInvite}
          onChange={(evenement) => setRoleInvite(evenement.target.value as RoleMembre)}
          className="h-9 rounded-md border border-border bg-canvas px-2 text-sm text-ink"
          aria-label="Rôle"
        >
          {ROLES.map((role) => (
            <option key={role.id} value={role.id}>
              {role.libelle}
            </option>
          ))}
        </select>
        <Button type="submit" disabled={enCours}>
          Inviter
        </Button>
      </form>
      <ul className="mt-8">
        {liste.map((membre) => (
          <li key={membre.email} className="flex items-center justify-between gap-4 border-b border-hairline py-4">
            <span className="text-sm font-medium text-ink">
              {membre.email}
              {membre.email === email ? " (vous)" : ""}
            </span>
            <select
              value={membre.role}
              aria-label={`Rôle de ${membre.email}`}
              onChange={async (evenement) => {
                const role = evenement.target.value as RoleMembre;
                try {
                  await changerRole(membre.email, role);
                  setMembres(await listerMembres());
                } catch (exception) {
                  setErreur(exception instanceof Error ? exception.message : "Échec du changement.");
                }
              }}
              className="h-9 rounded-md border border-border bg-canvas px-2 text-sm text-ink"
            >
              {ROLES.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.libelle}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </div>
  );
}
