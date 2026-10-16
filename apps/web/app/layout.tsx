import "./style.css";
export const metadata = {
  title: "Fincathon · Ruang Ekspor",
  description:
    "Perencanaan ekspor dengan bukti dan arus kas yang dapat ditelusuri.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
