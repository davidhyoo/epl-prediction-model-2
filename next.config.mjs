/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Tree-shake big icon/chart/UI barrels so pages only pull the exact modules
  // they use. Cuts dev-compile time and shrinks client bundles noticeably.
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-popover",
      "@radix-ui/react-scroll-area",
      "@radix-ui/react-select",
      "@radix-ui/react-separator",
      "@radix-ui/react-slot",
      "@radix-ui/react-switch",
      "@radix-ui/react-tabs",
      "@radix-ui/react-tooltip",
    ],
  },
  // Data is generated locally by the Python pipeline into /public/data,
  // so no remote image domains are required. Headshots are generated SVG avatars.
  images: {
    remotePatterns: [],
  },
  // Keep the dev console clean: don't print a line for every individual page
  // request (e.g. `GET /players/LEE-19 200`). Warnings/errors are still shown.
  logging: {
    incomingRequests: false,
  },
};

export default nextConfig;
