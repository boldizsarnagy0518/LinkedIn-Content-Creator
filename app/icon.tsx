import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#f4f5f2", border: "30px solid #161817", color: "#161817", fontFamily: "Georgia", fontSize: 150, fontWeight: 700 }}>
      CO<span style={{ color: "#d84f3d" }}>.</span>
    </div>,
    size
  );
}
