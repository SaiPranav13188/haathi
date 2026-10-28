import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Haathi – Find Government Schemes",
    short_name: "Haathi",
    description: "Find government schemes you're eligible for, in Telugu, Hindi or English, with proof from official rules.",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f0e4",
    theme_color: "#0b6e84",
    lang: "te",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-monochrome.svg", sizes: "any", type: "image/svg+xml", purpose: "monochrome" },
    ],
  };
}
