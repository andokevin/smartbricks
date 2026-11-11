/** Les 5 critères du matching, dans un ORDRE FIXE, avec leur couleur.
 *
 * Palette vérifiée avec le validateur de la référence dataviz (séparation pour les daltoniens
 * et vision normale : OK ; contraste < 3:1 pour 3 teintes → les contributions sont toujours
 * accompagnées d'étiquettes chiffrées, jamais la couleur seule).
 */
import type { CriterionKey } from "../api/types";

export const CRITERIA: { key: CriterionKey; label: string; color: string; better: string }[] = [
  { key: "cost", label: "Coût", color: "#1e5aa8", better: "moins cher" },
  { key: "speed", label: "Rapidité", color: "#eb6834", better: "plus rapide" },
  { key: "quality", label: "Qualité", color: "#1baf7a", better: "mieux noté" },
  { key: "availability", label: "Disponibilité", color: "#eda100", better: "plus disponible" },
  { key: "coverage", label: "Couverture", color: "#e87ba4", better: "couvre plus de tâches" },
];

export const PRESET_NAMES = ["Équilibré", "Économique", "Rapide", "Qualité"] as const;
