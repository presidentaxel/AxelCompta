"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { connexionGestionnaire, ErreurAuthGestionnaire } from "@/lib/auth-gestionnaire";

/** Connexion gestionnaire (doc 03 §7). Hors du groupe `(gestionnaire)` pour
 * ne pas hériter de la Sidebar/TopBar avant d'être connecté. */
export default function ConnexionGestionnairePage() {
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
      await connexionGestionnaire(email.trim(), motDePasse);
      router.push("/");
    } catch (exception) {
      setErreur(
        exception instanceof ErreurAuthGestionnaire ? exception.message : "Échec de la connexion.",
      );
    } finally {
      setEnCours(false);
    }
  }

  return (
    <main className="mx-auto mt-24 max-w-sm px-4">
      <h1 className="mb-1 text-xl font-bold text-ink">Connexion gestionnaire</h1>
      <p className="mb-6 text-sm text-subtle">Accédez à l&apos;état de votre portefeuille.</p>
      <form className="space-y-3" onSubmit={seConnecter}>
        <input
          type="email"
          value={email}
          onChange={(evenement) => setEmail(evenement.target.value)}
          placeholder="Votre e-mail"
          required
          disabled={enCours}
          className="w-full rounded-md border border-border px-3 py-2 text-sm"
        />
        <input
          type="password"
          value={motDePasse}
          onChange={(evenement) => setMotDePasse(evenement.target.value)}
          placeholder="Votre mot de passe"
          required
          disabled={enCours}
          className="w-full rounded-md border border-border px-3 py-2 text-sm"
        />
        {erreur && <p className="text-sm text-danger">{erreur}</p>}
        <button
          type="submit"
          disabled={enCours}
          className="w-full rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {enCours ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </main>
  );
}
