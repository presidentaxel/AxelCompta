"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  changerRole,
  ErreurAuthGestionnaire,
  integrerMembreSession,
  inviterMembre,
  lireEquipeSession,
  listerMembres,
  obtenirSessionGestionnaire,
  publierEquipeSession,
  type MembrePortefeuille,
  type RoleMembre,
} from "@/lib/auth-gestionnaire";

const ROLES: { id: RoleMembre; libelle: string; detail: string }[] = [
  { id: "admin", libelle: "Admin", detail: "Nom, équipe, retraits, règles" },
  { id: "membre", libelle: "Membre", detail: "Invitations et rappels" },
  { id: "lecture", libelle: "Lecture", detail: "Consultation" },
];

export default function EquipePage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [membres, setMembres] = useState<MembrePortefeuille[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [emailInvite, setEmailInvite] = useState("");
  const [roleInvite, setRoleInvite] = useState<RoleMembre>("membre");
  const [enCours, setEnCours] = useState(false);
  // Un chargement lancé avant une invitation ou un changement de rôle ne
  // réécrit pas la liste avec la réponse plus ancienne.
  const requeteCourante = useRef(0);

  function retenir(membre: MembrePortefeuille) {
    requeteCourante.current += 1;
    setMembres((actuels) => integrerMembreSession(actuels ?? [], membre));
  }

  useEffect(() => {
    const session = obtenirSessionGestionnaire();
    if (!session) {
      router.replace("/connexion");
      return;
    }
    // Lecture de sessionStorage avant le rafraîchissement réseau.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEmail(session.email);
    const memo = lireEquipeSession();
    if (memo) setMembres(memo);

    let ignore = false;
    const charger = () => {
      const id = ++requeteCourante.current;
      listerMembres()
        .then((liste) => {
          if (ignore || id !== requeteCourante.current) return;
          publierEquipeSession(liste);
          setMembres(liste);
        })
        .catch((exception) => {
          if (ignore || id !== requeteCourante.current) return;
          if (exception instanceof ErreurAuthGestionnaire) router.replace("/connexion");
          else if (!lireEquipeSession()) setErreur("Impossible de charger l'équipe.");
        });
    };
    charger();
    const surVisibilite = () => {
      if (document.visibilityState === "visible") charger();
    };
    document.addEventListener("visibilitychange", surVisibilite);
    return () => {
      ignore = true;
      document.removeEventListener("visibilitychange", surVisibilite);
    };
  }, [router]);

  const liste =
    membres && membres.length > 0
      ? membres
      : email
        ? [{ email, role: "admin" as const, statut: "actif" as const }]
        : [];

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Équipe</h1>
      <p className="mt-2 text-sm text-subtle">Qui voit cette organisation, et jusqu&apos;où.</p>
      {erreur && <p className="mt-6 text-sm text-danger">{erreur}</p>}

      <div className="mt-8 grid items-start gap-12 lg:grid-cols-3">
      <form
        className="space-y-4 lg:col-span-2"
        onSubmit={async (evenement) => {
          evenement.preventDefault();
          setEnCours(true);
          setErreur(null);
          try {
            const membre = await inviterMembre(emailInvite.trim(), roleInvite);
            setEmailInvite("");
            retenir(membre);
          } catch (exception) {
            setErreur(exception instanceof Error ? exception.message : "Échec de l'invitation.");
          } finally {
            setEnCours(false);
          }
        }}
      >
        <p className="text-sm font-medium text-ink">Inviter quelqu&apos;un</p>
        <Input
          type="email"
          required
          value={emailInvite}
          onChange={(evenement) => setEmailInvite(evenement.target.value)}
          placeholder="E-mail"
          disabled={enCours}
        />
        <Segment valeur={roleInvite} onChoisir={setRoleInvite} />
        <Button type="submit" disabled={enCours} className="w-full">
          Envoyer l&apos;invitation
        </Button>
      </form>
      <ul>
        {liste.map((membre) => (
          <li key={membre.email} className="border-b border-hairline py-4">
            <p className="text-sm font-medium text-ink">
              {membre.email}
              <span className="font-normal text-subtle">
                {" · "}
                {membre.statut === "actif" ? "Invitation acceptée" : "Invitation envoyée"}
                {membre.email === email ? " · vous" : ""}
              </span>
            </p>
            <div className="mt-3">
              <Segment
                valeur={membre.role}
                onChoisir={async (role) => {
                  if (role === membre.role) return;
                  try {
                    const misAJour = await changerRole(membre.email, role);
                    retenir(misAJour);
                  } catch (exception) {
                    setErreur(exception instanceof Error ? exception.message : "Échec du changement.");
                  }
                }}
              />
            </div>
          </li>
        ))}
      </ul>
      </div>
    </div>
  );
}

function Segment({
  valeur,
  onChoisir,
}: {
  valeur: RoleMembre;
  onChoisir: (role: RoleMembre) => void;
}) {
  return (
    <div className="flex w-full overflow-hidden rounded-md border border-border">
      {ROLES.map((role) => (
        <button
          key={role.id}
          type="button"
          title={role.detail}
          onClick={() => onChoisir(role.id)}
          className={`h-9 flex-1 border-l border-border text-sm first:border-l-0 ${
            valeur === role.id ? "bg-surface-soft font-medium text-ink" : "text-subtle hover:bg-canvas-app"
          }`}
        >
          {role.libelle}
        </button>
      ))}
    </div>
  );
}
