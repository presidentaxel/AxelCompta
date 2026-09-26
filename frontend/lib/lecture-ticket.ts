import type { TransactionVue } from "@/lib/types";

const ENSEIGNES_AUTRES = ["Le petit café", "Boulangerie du coin", "Pressing République"];

/** Ce que la lecture simulée a « lu » sur le ticket, et le mouvement le plus
 * proche. `ecart` vide : ça colle. L'OCR réel viendra plus tard : ici la
 * graine du fichier décide, de façon stable, match, montant ou enseigne. */
export type LectureTicket = {
  enseigne: string;
  montant_cts: number;
  date: string;
  mouvement: TransactionVue | null;
  ecart: null | "montant" | "enseigne" | "aucun";
};

export function nomCommercant(libelle: string): string {
  const trouve = libelle.match(/^(.*)\s+\(([a-z0-9_]+)\)$/);
  return (trouve?.[1] ?? libelle).trim();
}

export function graineFichier(fichier: { name: string; size: number }): number {
  let n = fichier.size >>> 0;
  for (let i = 0; i < fichier.name.length; i += 1) {
    n = (Math.imul(n, 33) + fichier.name.charCodeAt(i)) >>> 0;
  }
  return n;
}

export function simulerLectureTicket(graine: number, sansTicket: TransactionVue[]): LectureTicket {
  const mouvement = sansTicket[graine % Math.max(sansTicket.length, 1)];
  if (!mouvement) {
    return { enseigne: "Ticket", montant_cts: 0, date: "", mouvement: null, ecart: "aucun" };
  }
  const nom = nomCommercant(mouvement.libelle);
  const scenario = graine % 3;
  if (scenario === 0) {
    return { enseigne: nom, montant_cts: mouvement.montant_cts, date: mouvement.date, mouvement, ecart: null };
  }
  if (scenario === 1) {
    const delta = 5_00 + (graine % 40_00);
    const montant = mouvement.montant_cts < 0 ? mouvement.montant_cts - delta : mouvement.montant_cts + delta;
    return { enseigne: nom, montant_cts: montant, date: mouvement.date, mouvement, ecart: "montant" };
  }
  const enseigne = ENSEIGNES_AUTRES[graine % ENSEIGNES_AUTRES.length] ?? "Le petit café";
  return { enseigne, montant_cts: mouvement.montant_cts, date: mouvement.date, mouvement, ecart: "enseigne" };
}
