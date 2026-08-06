/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
