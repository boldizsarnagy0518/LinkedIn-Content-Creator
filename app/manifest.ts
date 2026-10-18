import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ContentOps",
    short_name: "ContentOps",
    description: "A human-controlled editorial workflow for LinkedIn content.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f5f2",
    theme_color: "#161817",
    icons: [{ src: "/icon", sizes: "512x512", type: "image/png" }]
  };
}
