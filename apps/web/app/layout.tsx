import "./style.css";
export const metadata = {
  title: "ALLExport · Export workspace",
  description:
    "Evidence-led export planning with traceable economics and cash flow.",
  icons: { icon: "/icon.png" },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
