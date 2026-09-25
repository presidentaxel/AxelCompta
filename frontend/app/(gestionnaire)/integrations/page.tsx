const PREVUES = [
  {
    nom: "Bridge",
    detail: "Connexion bancaire directe, en plus du canal déjà utilisé pour le pilote.",
  },
  {
    nom: "Volubile",
    detail: "Appels automatiques pour les rappels configurés dans Rappels.",
  },
  {
    nom: "SMS",
    detail: "Envoi des rappels par SMS.",
  },
  {
    nom: "E-mail",
    detail: "Envoi des rappels par e-mail, distinct de l'invitation de compte.",
  },
];

/** Présente ce que la V1 branchera. Aucun connecteur n'est activé ici. */
export default function IntegrationsPage() {
  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Intégrations</h1>
      <p className="mt-2 text-sm text-subtle">
        Ce que l&apos;application pourra brancher. Rien n&apos;est connecté depuis cet écran.
      </p>
      <ul className="mt-8">
        {PREVUES.map((integration) => (
          <li key={integration.nom} className="flex items-start justify-between gap-6 border-b border-hairline py-4">
            <span>
              <span className="block text-sm font-medium text-ink">{integration.nom}</span>
              <span className="mt-1 block text-sm text-subtle">{integration.detail}</span>
            </span>
            <span className="shrink-0 text-xs text-subtle">Prévu</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
