import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";

test("numeric drill-down resolves fixed input revisions and original source bytes", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
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
  await page
    .getByRole("button", { name: "Biaya & arus kas", exact: true })
    .click();
  const panel = page.locator(".numeric-lineage");
  await panel.locator("summary").first().click();
  const metric = panel.locator("article").first();
  await metric.getByText(/masukan versi tetap/).click();
  const input = metric.getByRole("button", { name: /^Masukan revisi/ }).first();
  await input.focus();
  await page.keyboard.press("Enter");
  const historical = panel.getByRole("complementary", {
    name: "Versi sumber tersimpan",
  });
  await expect(historical).toContainText(
    "Tinjauan historis tidak memberi izin tindakan baru",
  );
  await historical.locator("summary").click();
  const text = (await input.innerText()).split(" · ");
  const revision = text[0].split(" ").at(-1);
  const response = await context.request.get(
    "/api/gateway/inputs/" + text[1] + "/revisions/" + revision,
  );
  expect(response.ok()).toBe(true);
  const snapshot = (await response.json()).result;
  await expect(historical).toContainText(snapshot.id);
  await expect(historical).toContainText(
    snapshot.constraints.cash_snapshot.available.amount,
  );

  await metric
    .getByRole("button", { name: /^Sumber revisi/ })
    .first()
    .click();
  await expect(
    historical.getByRole("link", { name: "Unduh sumber asli" }),
  ).toBeVisible();
  await expect(historical).toContainText("synthetic_demo");
  await expect(historical).toContainText("Berlaku hingga:");
  const download = await context.request.get(
    (await historical
      .getByRole("link", { name: "Unduh sumber asli" })
      .getAttribute("href")) as string,
  );
  expect(download.ok()).toBe(true);
  const hash = createHash("sha256")
    .update(await download.body())
    .digest("hex");
  await expect(historical.locator("code")).toHaveText(hash);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
