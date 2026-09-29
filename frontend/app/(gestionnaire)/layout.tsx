import { Sidebar } from "@/components/Sidebar";

/** Habillage gestionnaire (PC/web) — doc 19 §7 : « même socle, deux
 * habillages ». Groupe de routes Next.js (`(gestionnaire)`, sans effet sur
 * l'URL) plutôt que codé en dur dans le layout racine, pour que `/chauffeur`
 * ait son propre habillage (`app/chauffeur/layout.tsx`) sans hériter de la
 * Sidebar/TopBar gestionnaire.
 */
export default function GestionnaireLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-pro flex h-screen overflow-hidden bg-canvas-app">
      <Sidebar />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-canvas-app">
        <main className="flex-1 px-9 py-7">{children}</main>
      </div>
    </div>
  );
}
