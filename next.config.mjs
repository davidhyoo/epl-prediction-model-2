/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Data is generated locally by the Python pipeline into /public/data,
  // so no remote image domains are required. Headshots are generated SVG avatars.
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
