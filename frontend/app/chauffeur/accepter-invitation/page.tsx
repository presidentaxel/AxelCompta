"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  accepterInvitation,
  definirMotDePasse,
  ErreurAuthChauffeur,
} from "@/lib/auth-chauffeur";

type Etape = "verification" | "definir_mot_de_passe" | "erreur";

/** Page cible du lien envoyé par `POST /dossiers/{id}/inviter` (doc 17 §9
 * bloc B) — Supabase redirige ici avec les jetons dans le fragment d'URL
 * (`#access_token=...`), jamais dans l'URL visible ni envoyé au serveur.
 *
 * **Infra requise côté Louis, pas du code** : ajouter
 * `.../chauffeur/accepter-invitation` aux "Redirect URLs" autorisées dans
 * le dashboard Supabase (Authentication → URL Configuration) — sinon
 * Supabase redirige vers sa propre page par défaut.
 */
export default function AccepterInvitationPage() {
  const router = useRouter();
  const [etape, setEtape] = useState<Etape>("verification");
  const [erreur, setErreur] = useState<string | null>(null);
  const [motDePasse, setMotDePasse] = useState("");
  const [dossierId, setDossierId] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    accepterInvitation(window.location.hash)
      .then((session) => {
        setDossierId(session.dossierId);
        setEtape("definir_mot_de_passe");
      })
      .catch((exception) => {
        setErreur(
          exception instanceof ErreurAuthChauffeur ? exception.message : "Lien invalide.",
        );
        setEtape("erreur");
      });
  }, []);

  async function valider(evenement: React.FormEvent) {
    evenement.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      await definirMotDePasse(motDePasse);
      router.push(`/chauffeur/${dossierId}`);
    } catch (exception) {
      setErreur(
        exception instanceof ErreurAuthChauffeur
          ? exception.message
          : "Échec de l'enregistrement du mot de passe.",
      );
    } finally {
      setEnCours(false);
    }
  }

  if (etape === "verification") {
    return <p className="text-sm text-subtle">Vérification de votre invitation…</p>;
  }

  if (etape === "erreur") {
    return (
      <div>
        <p className="text-sm text-danger">{erreur}</p>
        <p className="mt-2 text-sm text-subtle">
          Redemandez une invitation à votre gestionnaire, ou{" "}
          <a href="/chauffeur/login" className="text-primary hover:underline">
            connectez-vous
          </a>{" "}
          si vous avez déjà un mot de passe.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-ink">Bienvenue</h1>
      <p className="mb-6 text-sm text-subtle">
        Choisissez un mot de passe pour vos prochaines connexions.
      </p>
      <form className="space-y-3" onSubmit={valider}>
        <input
          type="password"
          value={motDePasse}
          onChange={(evenement) => setMotDePasse(evenement.target.value)}
          placeholder="Nouveau mot de passe"
          required
          minLength={8}
          disabled={enCours}
          className="w-full rounded-md border border-border px-3 py-2 text-sm"
        />
        {erreur && <p className="text-sm text-danger">{erreur}</p>}
        <button
          type="submit"
          disabled={enCours}
          className="w-full rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {enCours ? "Enregistrement…" : "Valider"}
        </button>
      </form>
    </div>
  );
}
