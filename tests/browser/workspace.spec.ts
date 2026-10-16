import { test, expect } from "@playwright/test";
test("seeded database journey uses the browser, API and worker", async ({
  page,
  context,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (e) => failures.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Masuk demo", exact: true }),
  ).toBeVisible();
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ruang kerja Anda" }),
  ).toBeVisible();
  const cookies = await context.cookies();
  const session = cookies.find((c) => c.name === "fincathon_session");
  expect(session?.httpOnly).toBe(true);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  const card = page
    .locator("article")
    .filter({ hasText: "Coffee" })
    .filter({ hasText: "Transaksi" })
    .first();
  await card.getByRole("button", { name: "Buka ruang kerja" }).click();
  await expect(
    page.getByRole("button", { name: "Hitung ulang analisis" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Hitung ulang analisis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page
    .getByRole("button", { name: "Biaya & arus kas", exact: true })
    .click();
  await expect(
    page.getByText("IDR 26000000.00", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("-52000000.00", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Bukti & dokumen", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sumber dan kutipan" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Ringkasan", exact: true }).click();
  await page.getByRole("button", { name: "Hitung ulang analisis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Ruang kerja Anda" }),
  ).toBeVisible();
  expect(failures).toEqual([]);
});
test("cross-origin browser mutations are refused", async ({ request }) => {
  const response = await request.post("/api/session", {
    headers: { Origin: "https://untrusted.example" },
    data: { user_id: "demo_id_owner" },
  });
  expect(response.status()).toBe(403);
});

test("funding comparison and analysis-bound draft use real worker outputs", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Coffee" })
    .filter({ hasText: "Transaksi" })
    .first()
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await page.getByRole("button", { name: "Hitung ulang analisis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page
    .getByRole("button", { name: "Skenario & pendanaan", exact: true })
    .click();
  await page.getByRole("button", { name: "Cari opsi pendanaan" }).click();
  await expect(
    page.getByRole("button", { name: "Hitung skenario pendanaan ini" }).first(),
  ).toBeVisible({ timeout: 20000 });
  await page
    .getByRole("button", { name: "Hitung skenario pendanaan ini" })
    .last()
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page
    .getByRole("button", { name: "Biaya & arus kas", exact: true })
    .click();
  await expect(
    page.getByText("IDR 23800000.00", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("7000000.00", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Draf & persetujuan", exact: true })
    .click();
  await page.getByRole("button", { name: "Buat draf dari analisis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page.locator("details").last().locator("summary").click();
  await expect(
    page.getByRole("link", { name: "Unduh draf" }).last(),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Unduh draf" }).last().click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/artifact/);
  const stream = await file.createReadStream();
  let text = "";
  for await (const part of stream!) text += part.toString();
  expect(text).toContain("160000000");
  expect(text).toContain("DRAF");
});

test("production review resolves only its goods gate and finance remains forbidden", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .locator("#identity")
    .selectOption("demo_id_production_procurement");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · blocked goods" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await page
    .getByRole("button", { name: "Kesiapan & jadwal", exact: true })
    .click();
  const section = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Inspeksi dan koreksi barang",
      exact: true,
    }),
  });
  await section.locator("select").first().selectOption("ready");
  await section.getByLabel("Hasil pengukuran jumlah (kg)").fill("10");
  await section
    .getByLabel("Bukti pendukung yang telah ditinjau")
    .selectOption({ index: 1 });
  await section
    .getByLabel("Alasan / catatan tinjauan")
    .fill("Synthetic measured inspection for browser acceptance");
  await section.getByRole("button", { name: "Simpan inspeksi barang" }).click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  await expect(
    page.getByText("GOODS_CONFORMITY", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Verifikasi sumber saldo awal" }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const workspace = await (
    await context.request.get(
      "/api/gateway/workspaces/demo_stage_blocked_goods",
    )
  ).json();
  const root = "deals/" + workspace.result.deal_id;
  const deal = await (await context.request.get("/api/gateway/" + root)).json();
  const receipts = await (
    await context.request.get("/api/gateway/" + root + "/receipts")
  ).json();
  const receipt = receipts.result.items.find(
    (r: { status: string }) => r.status === "verified",
  );
  const denied = await context.request.post(
    "/api/gateway/" + root + "/receipt-verifications",
    {
      headers: { Origin: "http://127.0.0.1:3000" },
      data: {
        expected_revision: deal.result.deal.revision,
        receipt_id: receipt.id,
        disposition: "reversed",
        evidence_ids: receipt.evidence_ids,
        reason: "Authorization denial test",
        settled_at: null,
      },
    },
  );
  expect(denied.status()).toBe(403);
  await section.locator("select").first().selectOption("nonconforming");
  await section
    .getByLabel("Alasan / catatan tinjauan")
    .fill("Restore the versioned nonconforming demonstration checkpoint");
  await section.getByRole("button", { name: "Simpan inspeksi barang" }).click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
});

test("edits survive reload and the completed checkpoint reconciles through HTTP", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  const description = page.getByLabel("Deskripsi produk", { exact: true });
  const original = await description.inputValue();
  const changed = original + " · browser persistence";
  await description.fill(changed);
  await page
    .getByRole("button", { name: "Simpan perubahan", exact: true })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  await page.reload();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await expect(description).toHaveValue(changed);
  await description.fill(original);
  await page
    .getByRole("button", { name: "Simpan perubahan", exact: true })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "← Semua ruang kerja" }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · reconciling" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await page
    .getByRole("button", { name: "Pembayaran & penutupan", exact: true })
    .click();
  await expect(
    page.getByText(
      "Pembeli lunas dan penutupan internal adalah dua status terpisah.",
      { exact: false },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Jalankan rekonsiliasi", exact: true })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluasi penutupan internal", exact: true })
    .click();
  await expect(
    page.getByText("Penutupan masih terblokir. Tinjau kondisi gerbang.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "← Semua ruang kerja" }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · closed" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  await page
    .getByRole("button", { name: "Pembayaran & penutupan", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Jalankan rekonsiliasi", exact: true })
    .click();
  await expect(page.getByText("Tersimpan.", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluasi penutupan internal", exact: true })
    .click();
  await expect(
    page.getByText("Transaksi ditutup setelah seluruh syarat terpenuhi.", {
      exact: true,
    }),
  ).toBeVisible();
  const workspace = await (
    await context.request.get("/api/gateway/workspaces/demo_stage_closed")
  ).json();
  const deal = await (
    await context.request.get("/api/gateway/deals/" + workspace.result.deal_id)
  ).json();
  expect(deal.result.deal.states.internal_closure).toBe("closed");
  expect(deal.result.deal.states.buyer_payment).toBe("paid");
});
