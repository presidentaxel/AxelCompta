"use client";

import { useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import { joindreJustificatifChauffeur } from "@/lib/auth-chauffeur";
import type { TransactionVue } from "@/lib/types";

/** doc 17 §9 Semaine 3, doc 19 §5.7 : « photo de justificatif au fil de
 * l'eau » — `capture="environment"` ouvre directement l'appareil photo sur
 * mobile plutôt que la galerie (comportement standard des navigateurs
 * mobiles sur ce type d'input, pas de lib dédiée nécessaire). Le contenu
 * n'est jamais lu côté serveur (pas d'OCR, doc 17 §8) — seule la présence
 * compte ici. */
export function JustificatifPhoto({
  dossierId,
  ecritureId,
  aJustificatif,
  onJointe,
}: {
  dossierId: string;
  ecritureId: string;
  aJustificatif: boolean;
  onJointe: (transaction: TransactionVue) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function joindre(fichier: File) {
    setEnCours(true);
    setErreur(null);
    try {
      const transaction = await joindreJustificatifChauffeur(dossierId, ecritureId, fichier);
      onJointe(transaction);
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi de la photo.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(evenement) => {
          const fichier = evenement.target.files?.[0];
          if (fichier) void joindre(fichier);
          evenement.target.value = ""; // permet de reprendre une photo si l'envoi échoue
        }}
      />
      <button
        type="button"
        disabled={enCours}
        onClick={() => inputRef.current?.click()}
        className={`rounded-md border px-2 py-1 text-xs font-semibold disabled:opacity-50 ${
          aJustificatif
            ? "border-success/30 bg-validated-subtle text-validated"
            : "border-border bg-canvas text-ink hover:bg-canvas-app"
        }`}
      >
        {aJustificatif ? "Photo jointe ✓" : enCours ? "Envoi…" : "Ajouter une photo"}
      </button>
      {erreur && <p className="mt-1 text-xs text-danger">{erreur}</p>}
    </div>
  );
}
