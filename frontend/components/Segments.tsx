"use client";

/** Choix entre deux ou trois vues d'un même écran : onglets compacts sur
 * fond doux, la vue active en blanc. */
export function Segments<T extends string>({
  valeur,
  options,
  onChange,
}: {
  valeur: T;
  options: { valeur: T; libelle: string }[];
  onChange: (valeur: T) => void;
}) {
  return (
    <div role="group" className="flex rounded-lg bg-surface-soft p-0.5">
      {options.map((option) => (
        <button
          key={option.valeur}
          type="button"
          aria-pressed={valeur === option.valeur}
          onClick={() => onChange(option.valeur)}
          className={`h-8 flex-1 rounded-md text-[13px] font-medium transition-colors duration-150 ${
            valeur === option.valeur
              ? "bg-canvas text-ink ring-1 ring-border"
              : "text-subtle hover:text-ink"
          }`}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  );
}
