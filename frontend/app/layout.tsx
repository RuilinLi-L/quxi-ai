import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "曲析 AI",
  description: "拍谱识别与曲式和声分析 Web 原型"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
