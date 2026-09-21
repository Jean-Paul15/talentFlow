/**
 * Retourne le secret JWT depuis l'environnement.
 * Aucune valeur par défaut : le service refuse de démarrer sans JWT_SECRET.
 */
export function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (!secret) {
    throw new Error('JWT_SECRET doit être défini dans l\'environnement');
  }
  return secret;
}
