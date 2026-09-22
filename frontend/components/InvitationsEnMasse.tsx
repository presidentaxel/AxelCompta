"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import { inviterEnMasse, type InvitationsMasse } from "@/lib/auth-gestionnaire";

const MAX_LIGNES = 500;

const LIBELLES: Record<string, string> = {
  invité: "Invitation envoyée",
  deja_invite: "Déjà invité",
  dossier_inconnu: "Dossier inconnu",
  email_invalide: "E-mail invalide",
  doublon_dans_le_lot: "Doublon dans le fichier",
  erreur: "Échec d'envoi",
};

/** Lit « dossier_id,email » (ou séparé par point-virgule / tabulation), une
 * paire par ligne ; ignore les lignes vides et un éventuel en-tête. */
function lireLignes(texte: string): { dossier_id: string; email: string }[] {
  return texte
    .split(/\r?\n/)
    .map((ligne) => ligne.split(/[,;\t]/).map((partie) => partie.trim()))
    .filter(([dossier, email]) => dossier && email && dossier.toLowerCase() !== "dossier_id")
    .map(([dossier_id, email]) => ({ dossier_id, email }));
}

/** doc 19 §3.1 : invitation en masse depuis une base clients. Un fichier ou un
 * collage, un aperçu du nombre de lignes, puis un résultat ligne par ligne :
 * les lignes en échec n'empêchent pas les autres. */
export function InvitationsEnMasse({ onTermine }: { onTermine: () => void }) {
  const [texte, setTexte] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [resultat, setResultat] = useState<InvitationsMasse | null>(null);

  const lignes = lireLignes(texte);
  const troploin = lignes.length > MAX_LIGNES;

  async function charger(evenement: React.ChangeEvent<HTMLInputElement>) {
    const fichier = evenement.target.files?.[0];
    if (fichier) setTexte(await fichier.text());
  }

  async function envoyer() {
    setEnCours(true);
    setErreur(null);
    try {
      setResultat(await inviterEnMasse(lignes));
      onTermine();
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section className="mt-8 rounded-lg border border-border bg-canvas p-5 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-ink">Inviter en masse</h2>
      <p className="mb-3 text-sm text-subtle">
        Une ligne par chauffeur : <code>dossier_id, e-mail</code>. {MAX_LIGNES} lignes au plus par
        envoi.
      </p>
      <input type="file" accept=".csv,.txt" onChange={charger} className="mb-2 text-sm" />
      <textarea
        value={texte}
        onChange={(evenement) => setTexte(evenement.target.value)}
        rows={5}
        placeholder="DEMO_karim, karim@exemple.fr"
        disabled={enCours}
        className="w-full rounded-md border border-border px-3 py-2 font-mono text-xs"
      />
      <div className="mt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={envoyer}
          disabled={enCours || lignes.length === 0 || troploin}
          className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {enCours ? "Envoi…" : `Inviter ${lignes.length} chauffeur(s)`}
        </button>
        {troploin && <span className="text-sm text-danger">Trop de lignes ({lignes.length}).</span>}
        {erreur && <span className="text-sm text-danger">{erreur}</span>}
      </div>
      {resultat && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-semibold text-ink">
            {resultat.nb_invitees} invitation(s) envoyée(s) sur {resultat.lignes.length} ligne(s).
          </p>
          <table className="w-full text-left text-xs">
            <tbody>
              {resultat.lignes.map((ligne, rang) => (
                <tr key={rang} className="border-t border-border">
                  <td className="py-1 pr-3 font-mono">{ligne.dossier_id}</td>
                  <td className="py-1 pr-3">{ligne.email}</td>
                  <td
                    className={`py-1 ${ligne.resultat === "invité" ? "text-amount-positive" : "text-subtle"}`}
                  >
                    {LIBELLES[ligne.resultat] ?? ligne.resultat}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
