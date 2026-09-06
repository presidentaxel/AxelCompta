// DESIGN.md : format monétaire français, Intl.NumberFormat obligatoire —
// jamais un formatage de montant fait main.
const FORMATEUR_EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
});

export function formatMontant(centimes: number): string {
  return FORMATEUR_EUR.format(centimes / 100);
}
