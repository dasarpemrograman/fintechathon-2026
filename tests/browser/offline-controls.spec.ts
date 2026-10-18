import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
async function enter(page: import("@playwright/test").Page, name: string) {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: name })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await expect(
    page.getByRole("button", { name: "Hitung ulang analisis" }),
  ).toBeVisible();
}
test("offline Calendar shows delivered, conflict resolution and revocation from persisted state", async ({
  page,
  context,
}) => {
  await enter(page, "Synthetic coffee · negotiation");
  await page
    .getByRole("button", { name: "Kesiapan & jadwal", exact: true })
    .click();
  const milestoneForm = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Catat milestone eksternal" }),
  });
  await milestoneForm
    .getByLabel("Tanggal lokal (Asia/Jakarta)")
    .fill("2026-11-01");
  await milestoneForm
    .getByLabel("Bukti pendukung yang telah ditinjau")
    .selectOption({ index: 1 });
  await milestoneForm
    .getByRole("button", { name: "Catat milestone", exact: true })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  const panel = page
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: "Kalender opsional" }) });
  await panel.locator("summary").click();
  await expect(
    panel.getByText("DEMO SINTETIS · tidak ada panggilan Google"),
  ).toBeVisible();
  await panel
    .getByRole("button", { name: "Hubungkan kalender demo", exact: true })
    .click();
  await expect(
    panel.getByText("Status koneksi: connected", { exact: false }),
  ).toBeVisible();
  const connection = await panel
    .getByRole("combobox", { name: "Koneksi kalender", exact: true })
    .inputValue();
  const checkbox = panel
    .getByRole("group", { name: "Milestone yang diproyeksikan" })
    .getByRole("checkbox")
    .first();
  await checkbox.check();
  const label = await checkbox.locator("..").innerText();
  const milestone = label.split(" · ").at(-1)!.trim();
  await panel
    .getByRole("button", { name: "Pratinjau proyeksi", exact: true })
    .click();
  await expect(
    panel.getByText("Hash proyeksi:", { exact: false }),
  ).toBeVisible();
  await panel
    .getByRole("button", { name: "Setujui hash proyeksi ini" })
    .click();
  await expect(
    panel.getByRole("button", {
      name: "Jalankan proyeksi demo yang disetujui",
    }),
  ).toBeEnabled();
  await panel
    .getByRole("button", { name: "Jalankan proyeksi demo yang disetujui" })
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "partial",
    { timeout: 20000 },
  );
  await expect(async () => {
    await panel
      .getByRole("button", { name: "Perbarui status proyeksi" })
      .click();
    await expect(panel.getByText(/status proyeksi: delivered/)).toBeVisible();
  }).toPass({ timeout: 20000 });
  const args = [
    "scripts/demo_calendar_conflict.py",
    "--connection",
    connection,
    "--milestone",
    milestone,
  ];
  if (process.env.FINCATHON_BROWSER_COMPOSE === "1")
    execFileSync(
      "docker",
      [
        "compose",
        "-f",
        "compose.yaml",
        "-f",
        "compose.demo.yaml",
        "exec",
        "-T",
        "api",
        "python",
        ...args,
      ],
      { timeout: 20000 },
    );
  else
    execFileSync(".venv/bin/python", args, {
      env: { ...process.env, APP_MODE: "demo" },
      timeout: 20000,
    });
  await panel.getByRole("button", { name: "Perbarui status proyeksi" }).click();
  await expect(panel.getByText(/status proyeksi: conflict/)).toBeVisible();
  await panel
    .getByRole("button", { name: "Pertahankan perubahan eksternal" })
    .click();
  await expect(
    panel.getByText(/status proyeksi: external_retained/),
  ).toBeVisible();
  await panel.getByRole("button", { name: "Cabut koneksi ini" }).click();
  await expect(
    panel.getByText("Status koneksi: revoked", { exact: false }),
  ).toBeVisible();
  const persisted = (
    await (
      await context.request.get("/api/gateway/calendar/connections")
    ).json()
  ).result.items.find((row: { id: string }) => row.id === connection);
  expect(persisted.status).toBe("revoked");
  expect(persisted.data_mode).toBe("synthetic_demo");
});
test("public-source demo preview and discovery retain synthetic provider receipts", async ({
  page,
}) => {
  await enter(page, "Synthetic coffee · negotiation");
  await page
    .getByRole("button", { name: "Bukti & dokumen", exact: true })
    .click();
  const panel = page.locator("details").filter({
    has: page.locator("summary", {
      hasText: "Riset sumber publik menurut produk dan yurisdiksi",
    }),
  });
  await panel.locator("summary").click();
  await panel
    .getByRole("button", { name: "Pratinjau penggunaan riset" })
    .click();
  await expect(panel.getByRole("status")).toContainText("0 jatah riset");
  await panel
    .getByRole("button", { name: "Mulai riset dengan batas ini" })
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    { timeout: 20000 },
  );
  await page
    .getByTestId("job-state")
    .getByText("Jejak akses sumber dan penyedia")
    .click();
  await expect(page.getByTestId("job-state")).toContainText("synthetic_demo");
});
test("pending seller payment can be verified and reversed through the browser", async ({
  page,
  context,
}) => {
  const amount = "1." + Date.now().toString();
  await enter(page, "Synthetic coffee · reconciling");
  await page
    .getByRole("button", { name: "Pembayaran & penutupan", exact: true })
    .click();
  const workspace = (
    await (
      await context.request.get(
        "/api/gateway/workspaces/demo_stage_reconciling",
      )
    ).json()
  ).result;
  const deal = (
    await (
      await context.request.get("/api/gateway/deals/" + workspace.deal_id)
    ).json()
  ).result.deal;
  const seller = deal.parties.find((p: { roles: string[] }) =>
    p.roles.includes("seller"),
  ).id;
  const obligations = (
    await (
      await context.request.get(
        "/api/gateway/deals/" + deal.id + "/obligations",
      )
    ).json()
  ).result.items;
  const obligation = obligations.find(
    (row: { payer_party_id: string; status: string }) =>
      row.payer_party_id === seller && row.status === "open",
  );
  expect(obligation).toBeTruthy();
  const form = page.locator("details").filter({
    has: page.locator("summary", {
      hasText: "Catat bukti pembayaran pending",
    }),
  });
  await form.locator("summary").click();
  await form
    .getByRole("combobox", { name: "Kewajiban", exact: true })
    .selectOption(obligation.id);
  await form.getByLabel("Jumlah diterima", { exact: true }).fill(amount);
  await form.getByLabel("Tanggal nilai", { exact: true }).fill("2026-10-15");
  await form.getByRole("button", { name: "Simpan bukti pending" }).click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  const review = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Verifikasi dan koreksi bukti pembayaran",
    }),
  });
  let receipt = review
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: amount }) })
    .last();
  await receipt.locator("summary").click();
  await receipt
    .getByLabel("Waktu penyelesaian yang diketahui (UTC, opsional)")
    .fill("2026-10-15T12:00");
  await receipt
    .getByLabel("Bukti pendukung yang telah ditinjau")
    .selectOption({ index: 1 });
  await receipt
    .getByLabel("Alasan / catatan tinjauan")
    .fill("Offline evaluator verified seller transfer");
  await receipt
    .getByRole("button", { name: "Simpan tinjauan pembayaran" })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  receipt = review
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: amount }) })
    .last();
  await expect(receipt.locator("summary")).toContainText("Terverifikasi");
  if (!(await receipt.getAttribute("open")))
    await receipt.locator("summary").click();
  await receipt
    .getByLabel("Bukti pendukung yang telah ditinjau")
    .selectOption({ index: 1 });
  await receipt
    .getByLabel("Alasan / catatan tinjauan")
    .fill(
      "Reverse the synthetic evaluator transfer and restore the checkpoint",
    );
  await receipt
    .getByRole("button", { name: "Simpan tinjauan pembayaran" })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  const actual = (
    await (
      await context.request.get(
        "/api/gateway/deals/" + deal.id + "/obligations/" + obligation.id,
      )
    ).json()
  ).result;
  expect(actual.status).toBe("open");
});

test("keyboard navigation works on a narrow screen and labels remain readable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.locator("#identity").focus();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Masuk demo", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Ruang kerja Anda" }),
  ).toBeVisible();
  const open = page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Buka ruang kerja" });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Hitung ulang analisis" }),
  ).toBeVisible();
  const economics = page.getByRole("button", {
    name: "Biaya & arus kas",
    exact: true,
  });
  await economics.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Biaya yang dinyatakan" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: ".local/screenshots/mobile-economics.png" });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: ".local/screenshots/desktop-economics.png" });
});

test("editing opening cash persists and requires a fresh resource review", async ({
  page,
  context,
}) => {
  await enter(page, "Synthetic coffee · negotiation");
  const workspace = (
    await (
      await context.request.get(
        "/api/gateway/workspaces/demo_stage_negotiation",
      )
    ).json()
  ).result;
  const path = "/api/gateway/deals/" + workspace.deal_id;
  const before = (await (await context.request.get(path)).json()).result.deal;
  const panel = page.locator("details").filter({
    has: page.locator("summary", { hasText: "Batas dan preferensi pemilik" }),
  });
  await panel.locator("summary").click();
  await panel
    .getByRole("combobox", { name: "Bukti yang telah ditinjau", exact: true })
    .selectOption({ index: 1 });
  await panel
    .getByLabel("Alasan perubahan batas pemilik")
    .fill("Review a synthetic updated bank opening balance");
  await panel
    .getByLabel("Komitmen di luar transaksi", { exact: true })
    .fill("");
  await panel.getByRole("button", { name: "Simpan batas pemilik" }).click();
  await expect(panel.getByRole("alert")).toContainText("Lengkapi saldo");
  const unchanged = (await (await context.request.get(path)).json()).result
    .deal;
  expect(unchanged.revision).toBe(before.revision);
  await panel
    .getByLabel("Komitmen di luar transaksi", { exact: true })
    .fill(before.constraints.cash_snapshot.committed_elsewhere.amount);
  const changed =
    before.constraints.cash_snapshot.available.amount === "50000001"
      ? "50000002"
      : "50000001";
  await panel.getByLabel("Saldo tersedia", { exact: true }).fill(changed);
  await panel.getByRole("button", { name: "Simpan batas pemilik" }).click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  const actual = (await (await context.request.get(path)).json()).result.deal;
  expect(actual.constraints.cash_snapshot.available.amount).toBe(changed);
  expect(actual.constraints.allowable_changes).toContain("funding");
  const gate = (
    await (await context.request.get(path + "/readiness?stage=shipment")).json()
  ).result;
  expect(
    gate.conditions.find(
      (row: { code: string }) => row.code === "VERIFIED_OPENING_RESOURCES",
    ).status,
  ).toBe("unresolved");
  await panel
    .getByLabel("Saldo tersedia", { exact: true })
    .fill(before.constraints.cash_snapshot.available.amount);
  await panel
    .getByRole("combobox", { name: "Bukti yang telah ditinjau", exact: true })
    .selectOption({ index: 1 });
  await panel
    .getByLabel("Alasan perubahan batas pemilik")
    .fill("Restore the evaluator opening amount");
  await panel.getByRole("button", { name: "Simpan batas pemilik" }).click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  expect(
    (await (await context.request.get(path)).json()).result.deal.constraints
      .cash_snapshot.available.amount,
  ).toBe(before.constraints.cash_snapshot.available.amount);
});
