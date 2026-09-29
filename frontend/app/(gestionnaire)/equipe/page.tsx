"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pastille } from "@/components/Pastille";
import { Segments } from "@/components/Segments";
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
    <div className="mx-auto max-w-[1100px]">
      <h1 className="text-[22px] font-medium tracking-tight text-ink">Équipe</h1>
      <p className="mt-1 text-[13.5px] text-subtle">Qui voit cette organisation, et jusqu&apos;où.</p>
      {erreur && <p className="mt-5 text-sm text-danger">{erreur}</p>}

      <form
        className="mt-6 flex flex-wrap items-center gap-2"
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
        <Input
          type="email"
          required
          value={emailInvite}
          onChange={(evenement) => setEmailInvite(evenement.target.value)}
          placeholder="E-mail de la personne à inviter"
          aria-label="E-mail de la personne à inviter"
          disabled={enCours}
          className="w-72"
        />
        <div className="w-60">
          <Segment label="Rôle de la personne invitée" valeur={roleInvite} onChoisir={setRoleInvite} />
        </div>
        <Button type="submit" disabled={enCours}>
          Envoyer l&apos;invitation
        </Button>
      </form>

      <table className="mt-7 w-full border-collapse text-[13.5px]">
        <thead>
          <tr className="border-b border-border text-left text-[11.5px] font-medium tracking-wide text-muted">
            <th className="pb-2 pr-3">Personne</th>
            <th className="w-[200px] pb-2 pr-3">Statut</th>
            <th className="w-[260px] pb-2">Rôle</th>
          </tr>
        </thead>
        <tbody>
          {liste.map((membre) => (
            <tr key={membre.email} className="border-b border-hairline">
              <td className="py-3 pr-3 font-medium text-ink">
                {membre.email}
                {membre.email === email && (
                  <span className="ml-2 inline-flex h-[22px] items-center rounded-sm bg-surface-soft px-2 text-xs font-medium text-subtle">
                    vous
                  </span>
                )}
              </td>
              <td className="py-3 pr-3">
                {membre.statut === "actif" ? (
                  <Pastille ton="positif" point>
                    Invitation acceptée
                  </Pastille>
                ) : (
                  <Pastille ton="attention" point>
                    Invitation envoyée
                  </Pastille>
                )}
              </td>
              <td className="py-3">
                <Segment
                  label={`Rôle de ${membre.email}`}
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
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Segment({
  valeur,
  onChoisir,
  label,
}: {
  valeur: RoleMembre;
  onChoisir: (role: RoleMembre) => void;
  label: string;
}) {
  return (
    <Segments
      label={label}
      valeur={valeur}
      onChange={onChoisir}
      options={ROLES.map((role) => ({ valeur: role.id, libelle: role.libelle }))}
    />
  );
}
