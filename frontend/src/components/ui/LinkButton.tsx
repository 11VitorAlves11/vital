import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { buttonClasses, type ButtonVariant } from "./Button";

type LinkButtonProps = {
  to: string;
  variant?: ButtonVariant;
  className?: string;
  children: ReactNode;
};

/** Navigation that looks like an action. Still a link, so it opens in a new tab
 * and reads as a link to assistive technology. */
export function LinkButton({ to, variant = "primary", className, children }: LinkButtonProps) {
  return (
    <Link to={to} className={buttonClasses(variant, className)}>
      {children}
    </Link>
  );
}
