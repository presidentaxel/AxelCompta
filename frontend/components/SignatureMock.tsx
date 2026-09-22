"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

/** doc 17 §9 Semaine 3, doc 17 §8 : signature « vrai faux » — décidé avec
 * Louis le 2026-09-07 (aucun prestataire choisi, ADR-004 toujours en
 * attente). Volontairement pas persistée (état local, perdu au
 * rechargement) : ce n'est pas une décision humaine à tracer comme
 * `DecisionHumaine` (doc 05 §5), juste un écran qui montre où ce moment
 * du parcours (doc 19 §5.8) prendra place une fois un prestataire choisi. */
export function SignatureMock({ nomDocument }: { nomDocument: string }) {
  const [signe, setSigne] = useState(false);

  return (
    <div className="rounded-md border border-border bg-canvas p-3">
      <p className="mb-2 text-sm text-ink">{nomDocument}</p>
      {signe ? (
        <p className="text-sm font-semibold text-validated">✓ Signé (démo — pas de valeur légale)</p>
      ) : (
        <Button type="button" variant="secondary" size="sm" onClick={() => setSigne(true)}>
          Signer
        </Button>
      )}
    </div>
  );
}
