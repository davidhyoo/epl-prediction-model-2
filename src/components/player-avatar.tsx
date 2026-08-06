"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { initials, stringToHue } from "@/lib/format";

const SIZES = {
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-14 text-lg",
  xl: "size-20 text-2xl",
};

interface PlayerAvatarProps {
  name: string;
  /** Optional headshot URL. When absent (the default), a clean initials
   *  avatar is generated — no scraping, always legal. */
  src?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}

/**
 * Player avatar. We deliberately generate a deterministic initials avatar
 * rather than scraping copyrighted headshots. If a legally-sourced `src`
 * is provided it is used, with the initials as the fallback.
 */
export function PlayerAvatar({ name, src, size = "md", className }: PlayerAvatarProps) {
  const [broken, setBroken] = React.useState(false);
  const hue = stringToHue(name);
  const bg = `hsl(${hue} 60% 45%)`;
  const bg2 = `hsl(${(hue + 40) % 360} 62% 38%)`;
  const showImage = Boolean(src) && !broken;

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-semibold text-white ring-2 ring-background",
        SIZES[size],
        className,
      )}
      style={{ backgroundImage: `linear-gradient(135deg, ${bg}, ${bg2})` }}
      aria-hidden={!name}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src as string}
          alt={name}
          loading="lazy"
          className="h-full w-full object-cover"
          onError={() => setBroken(true)}
        />
      ) : (
        <span>{initials(name)}</span>
      )}
    </span>
  );
}
