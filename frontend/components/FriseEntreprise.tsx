/** Le compte se prépare une fois. Ensuite, par exercice : clôture, signature
 * de validation, dépôt au greffe, dépôt aux impôts, signature légale
 * (doc 02 §4 et §6, doc 19 §5.3, doc 20 §4bis). */
export const ETAPES = ["Compte", "Clôture", "Signature", "Greffe", "Impôts", "Signature légale"];

/** Rang de l'étape atteinte : -1 tant que rien n'est fait. */
export function rangEtape(etape: string, compteOuvert: boolean): number {
  if (etape === "Suivi" || (etape === "Compte" && compteOuvert)) return ETAPES.indexOf("Compte");
  if (etape === "Signé") return ETAPES.indexOf("Greffe");
  const index = ETAPES.indexOf(etape);
  return etape === "Compte" ? -1 : index;
}

/** Nom de l'étape en clair, pour la ligne repliée. */
export function libelleEtape(etape: string, rang: number): string {
  if (etape === "Sans exercice") return "Sans exercice";
  if (rang < 0) return "Compte fermé";
  return ETAPES[rang] ?? etape;
}

/** Ligne repliée : six segments et le nom de l'étape en cours. */
export function MiniFrise({
  annee,
  etape,
  compteOuvert,
}: {
  annee: number;
  etape: string;
  compteOuvert: boolean;
}) {
  const rang = rangEtape(etape, compteOuvert);
  const libelle = libelleEtape(etape, rang);
  return (
    <span className="flex items-center gap-2 text-xs leading-none">
      <span className="w-7 shrink-0 tabular-nums text-muted">{annee}</span>
      <span className="flex w-24 shrink-0 gap-0.5" aria-hidden>
        {ETAPES.map((nom, index) => (
          <span
            key={nom}
            className={`h-1 flex-1 rounded-sm ${index <= rang ? "bg-ink" : "bg-border"}`}
          />
        ))}
      </span>
      <span className={rang < 0 ? "text-muted" : "text-subtle"}>{libelle}</span>
    </span>
  );
}

/** Ligne dépliée : les six étapes nommées, l'étape en cours en rouille. */
export function FriseDetaillee({
  annee,
  etape,
  compteOuvert,
}: {
  annee: number;
  etape: string;
  compteOuvert: boolean;
}) {
  const rang = rangEtape(etape, compteOuvert);
  return (
    <div className="flex items-start gap-3.5">
      <span className="w-8 shrink-0 text-xs leading-none tabular-nums text-muted">{annee}</span>
      <ol className="grid min-w-0 flex-1 grid-cols-6">
        {ETAPES.map((nom, index) => {
          const fait = index <= rang;
          const courant = index === rang;
          return (
            <li key={nom} className="relative flex flex-col items-center">
              {index > 0 && (
                <span
                  className={`absolute left-0 right-1/2 top-[3px] h-px ${fait ? "bg-ink" : "bg-border"}`}
                />
              )}
              {index < ETAPES.length - 1 && (
                <span
                  className={`absolute left-1/2 right-0 top-[3px] h-px ${index < rang ? "bg-ink" : "bg-border"}`}
                />
              )}
              <span
                className={`relative z-10 h-2 w-2 rounded-full ${
                  courant ? "bg-primary ring-[3px] ring-primary-subtle" : fait ? "bg-ink" : "bg-border-strong"
                }`}
              />
              <span
                className={`mt-1.5 text-center text-[11.5px] leading-tight ${
                  courant ? "font-medium text-primary" : fait ? "text-ink" : "text-muted"
                }`}
              >
                {nom}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
