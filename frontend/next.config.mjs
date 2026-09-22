/** @type {import('next').NextConfig} */
const nextConfig = {
  // Next 16 régénère sinon AGENTS.md/CLAUDE.md (boilerplate générique) à
  // chaque `next dev` — le projet a déjà sa propre documentation (docs/,
  // DESIGN.md), pas besoin d'un doublon générique non versionné.
  agentRules: false,
};

export default nextConfig;
