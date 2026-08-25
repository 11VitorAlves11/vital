import { useIsDesktop } from "../../lib/useMediaQuery";
import { Dialog, type SurfaceProps } from "./Dialog";
import { Sheet } from "./Sheet";

/**
 * Resolves the one decision every form in the app shares: a full-screen Sheet on
 * a phone, a modal Dialog on a desktop. Pages state what the form is, not where.
 */
export function FormSurface(props: SurfaceProps) {
  return useIsDesktop() ? <Dialog {...props} /> : <Sheet {...props} />;
}
