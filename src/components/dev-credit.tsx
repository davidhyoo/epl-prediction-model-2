import * as React from "react";
import { cn } from "@/lib/utils";

export const LINKEDIN_URL = "https://www.linkedin.com/in/david-h-yoo";
export const GITHUB_URL = "https://github.com/davidhyoo/epl-prediction-model-2";

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.55V9h3.57v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.55C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.72C24 .77 23.2 0 22.22 0z" />
    </svg>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58l-.01-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.74.08-.74 1.2.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.96 0-1.32.47-2.39 1.24-3.23-.12-.3-.54-1.53.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6.01 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.77.84 1.24 1.91 1.24 3.23 0 4.63-2.81 5.65-5.49 5.95.43.37.81 1.1.81 2.22l-.01 3.29c0 .32.22.7.83.58A12.01 12.01 0 0 0 24 12.5C24 5.87 18.63.5 12 .5z" />
    </svg>
  );
}

/**
 * Slim, sitewide developer credit shown above the main navigation.
 * Links out to the author's LinkedIn and the project's GitHub repository.
 */
export function DevCreditBar() {
  return (
    <div className="w-full border-b border-border/60 bg-secondary/40 text-xs">
      <div className="container-page flex h-8 items-center justify-end gap-3">
        <span className="text-muted-foreground">
          Developed by <span className="font-medium text-foreground">David Yoo</span>
        </span>
        <div className="flex items-center gap-1">
          <CreditLink href={LINKEDIN_URL} label="David Yoo on LinkedIn">
            <LinkedInIcon className="size-3.5" />
          </CreditLink>
          <CreditLink href={GITHUB_URL} label="Project on GitHub">
            <GitHubIcon className="size-3.5" />
          </CreditLink>
        </div>
      </div>
    </div>
  );
}

function CreditLink({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-6 items-center justify-center rounded-md text-muted-foreground",
        "transition-colors hover:bg-secondary hover:text-foreground",
      )}
    >
      {children}
    </a>
  );
}

/** Inline social links reused in the footer. */
export function DevCreditLinks({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <a
        href={LINKEDIN_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="David Yoo on LinkedIn"
        className="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
      >
        <LinkedInIcon className="size-4" />
        <span>LinkedIn</span>
      </a>
      <span className="text-border">·</span>
      <a
        href={GITHUB_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Project on GitHub"
        className="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
      >
        <GitHubIcon className="size-4" />
        <span>GitHub</span>
      </a>
    </div>
  );
}
