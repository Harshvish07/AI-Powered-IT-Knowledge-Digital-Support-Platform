// Mirrors the backend's password policy (app/utils/validation.py) so users get
// immediate feedback; the backend re-validates regardless, as the source of truth.
export function getPasswordStrengthError(password: string): string | null {
  if (password.length < 8) return "Password must be at least 8 characters long.";
  if (!/[a-z]/.test(password)) return "Password must contain at least one lowercase letter.";
  if (!/[A-Z]/.test(password)) return "Password must contain at least one uppercase letter.";
  if (!/\d/.test(password)) return "Password must contain at least one digit.";
  if (!/[^\w\s]/.test(password)) return "Password must contain at least one special character.";
  return null;
}
