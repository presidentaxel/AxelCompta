"use client";

import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/** Filtre compact : « Libellé valeur » avec un menu. Remplace les pilules qui
 * changeaient de valeur au clic et n'ouvraient leur liste qu'à l'appui long. */
export function Selecteur<T extends string>({
  libelle,
  valeur,
  options,
  onChoisir,
}: {
  libelle: string;
  valeur: T;
  options: { id: T; libelle: string }[];
  onChoisir: (id: T) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const racine = useRef<HTMLSpanElement>(null);
  const declencheur = useRef<HTMLButtonElement>(null);
  const affiche = options.find((option) => option.id === valeur)?.libelle ?? valeur;

  useEffect(() => {
    if (!ouvert) return;
    function dehors(evenement: MouseEvent) {
      if (!racine.current?.contains(evenement.target as Node)) setOuvert(false);
    }
    function echap(evenement: KeyboardEvent) {
      if (evenement.key === "Escape") {
        setOuvert(false);
        declencheur.current?.focus();
      }
    }
    document.addEventListener("mousedown", dehors);
    document.addEventListener("keydown", echap);
    return () => {
      document.removeEventListener("mousedown", dehors);
      document.removeEventListener("keydown", echap);
    };
  }, [ouvert]);

  return (
    <span ref={racine} className="relative">
      <button
        ref={declencheur}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={ouvert}
        onClick={() => setOuvert(!ouvert)}
        className="inline-flex h-[34px] items-center gap-2 rounded-md border border-border-strong bg-canvas pl-3 pr-2.5 text-[13.5px] text-ink transition-colors duration-150 hover:border-ink"
      >
        <span className="text-muted">{libelle}</span>
        {affiche}
        <ChevronDown className="h-3.5 w-3.5 text-muted" aria-hidden />
      </button>
      {ouvert && (
        <span
          role="listbox"
          aria-label={libelle}
          className="absolute left-0 z-20 mt-1 flex min-w-44 flex-col rounded-md border border-border bg-canvas p-1"
        >
          {options.map((option) => (
            <button
              key={option.id}
              type="button"
              role="option"
              aria-selected={option.id === valeur}
              className="flex items-center justify-between gap-4 rounded-sm px-2.5 py-1.5 text-left text-[13.5px] text-ink hover:bg-surface-soft"
              onClick={() => {
                onChoisir(option.id);
                setOuvert(false);
                declencheur.current?.focus();
              }}
            >
              {option.libelle}
              {option.id === valeur && <Check className="h-3.5 w-3.5" aria-hidden />}
            </button>
          ))}
        </span>
      )}
    </span>
  );
}
