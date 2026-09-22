"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { connexionParMotDePasse, ErreurAuthChauffeur } from "@/lib/auth-chauffeur";

/** doc 19 §5.2 : « e-mail + mot de passe (ou lien magique), pas de
 * self-signup libre, mais un vrai compte personnel ». Un chauffeur qui n'a
 * jamais défini de mot de passe arrive ici depuis le lien d'invitation
 * (`/chauffeur/accepter-invitation`), pas depuis cet écran.
 */
export default function ConnexionChauffeurPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function seConnecter(evenement: React.FormEvent) {
    evenement.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      const session = await connexionParMotDePasse(email.trim(), motDePasse);
      router.push(`/chauffeur/${session.dossierId}`);
    } catch (exception) {
      setErreur(
        exception instanceof ErreurAuthChauffeur ? exception.message : "Échec de la connexion.",
      );
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-ink">Connexion</h1>
      <p className="mb-6 text-sm text-subtle">Retrouvez vos transactions et vos justificatifs.</p>
      <form className="space-y-3" onSubmit={seConnecter}>
        <Input
          type="email"
          uiSize="lg"
          value={email}
          onChange={(evenement) => setEmail(evenement.target.value)}
          placeholder="Votre e-mail"
          required
          disabled={enCours}
        />
        <Input
          type="password"
          uiSize="lg"
          value={motDePasse}
          onChange={(evenement) => setMotDePasse(evenement.target.value)}
          placeholder="Votre mot de passe"
          required
          disabled={enCours}
        />
        {erreur && <p className="text-sm text-danger">{erreur}</p>}
        <Button type="submit" disabled={enCours} className="w-full">
          {enCours ? "Connexion…" : "Se connecter"}
        </Button>
      </form>
    </div>
  );
}
