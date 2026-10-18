import { test, expect } from "@playwright/test";
import type { components } from "../../packages/contracts/api";
type S = components["schemas"];

test("comparison explains immutable joint changes, timing and risk without amending the deal", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Masuk demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Buka ruang kerja" })
    .click();
  const workspace = (
    await (
      await context.request.get(
        "/api/gateway/workspaces/demo_stage_negotiation",
      )
    ).json()
  ).result;
  const root = "/api/gateway/deals/" + workspace.deal_id;
  const original: S["Deal"] = (await (await context.request.get(root)).json())
    .result.deal;
  await page
    .getByRole("button", { name: "Skenario & pendanaan", exact: true })
    .click();
  await page
    .getByText("Negosiasikan ketentuan pembeli, pemasok dan produksi", {
      exact: true,
    })
    .click();
  const buyer = original.payment_terms.filter((term) => term.side === "buyer");
  expect(buyer).toHaveLength(2);
  for (const term of buyer)
    await page
      .getByLabel("Jumlah cicilan " + term.id, { exact: true })
      .fill("80000000");
  const supplier = original.payment_terms.find(
    (term) => term.side === "supplier",
  )!;
  await page
    .getByLabel("Waktu pembayaran " + supplier.id, { exact: true })
    .fill("2026-08-05T12:00:00Z");
  const acceptedPromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname.endsWith("/scenarios"),
  );
  await page
    .getByRole("button", {
      name: "Bandingkan seluruh usulan bersama",
      exact: true,
    })
    .click();
  const accepted = await acceptedPromise;
  expect(accepted.status()).toBe(202);
  const scenario: S["Scenario"] = (await accepted.json()).result.scenario;
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    /succeeded|partial/,
    { timeout: 30000 },
  );
  const analyses: S["Analysis"][] = (
    await (await context.request.get(root + "/analyses?limit=100")).json()
  ).result.items;
  const analysis = analyses.find((row) => row.scenario_id === scenario.id)!;
  expect(analysis).toBeTruthy();
  const before: S["Deal"] = (await (await context.request.get(root)).json())
    .result.deal;
  expect(before.payment_terms).toEqual(original.payment_terms);
  expect(before.procurement).toEqual(original.procurement);
  const base: S["Deal"] = (
    await (
      await context.request.get(
        "/api/gateway/inputs/" +
          scenario.base_revision.id +
          "/revisions/" +
          scenario.base_revision.revision,
      )
    ).json()
  ).result;
  const row = page.locator('[data-analysis-id="' + analysis.id + '"]');
  await row
    .getByRole("button", { name: "Lihat perubahan, jadwal & risiko" })
    .focus();
  await page.keyboard.press("Enter");
  await expect(row).toContainText("Usulan hipotetis");
  await expect(row).toContainText("revisi " + scenario.base_revision.revision);
  await expect(row).toContainText(
    analysis.after_financing.contribution!.amount,
  );
  await expect(row).toContainText(analysis.cash_metrics!.minimum_cash);
  await expect(row).toContainText("Horizon kewajiban:");
  const horizon = await page.evaluate(
    ({ instant, zone }) =>
      new Intl.DateTimeFormat("id-ID", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: zone,
      }).format(new Date(instant)),
    { instant: analysis.cash_metrics!.horizon_end, zone: base.owner_timezone },
  );
  await expect(row).toContainText(
    "Horizon kewajiban: " + horizon + " · " + base.owner_timezone,
  );
  await expect(row).toContainText("Eksposur piutang belum tertagih:");
  await expect(row).toContainText(
    analysis.owner_comparison!.buyer_receivable_exposure!.amount,
  );
  const patch = scenario.patches.find((item) => item.path === "/payment_terms");
  await row.locator("summary").filter({ hasText: "/payment_terms" }).click();
  await expect(row).toContainText("Nilai sebelum usulan");
  await expect(row).toContainText("Nilai sesudah usulan");
  await expect(row).toContainText(base.payment_terms[0].amount!.amount);
  await expect(row).toContainText(
    (patch!.value as S["Deal"]["payment_terms"])[0].amount!.amount,
  );
  expect(
    (patch!.value as S["Deal"]["payment_terms"])[0].amount!.amount,
  ).not.toBe(base.payment_terms[0].amount!.amount);
  await row.getByText("Jadwal arus kas versi ini", { exact: true }).click();
  await expect(
    row.getByRole("columnheader", { name: "Waktu", exact: true }),
  ).toBeVisible();
  const after = (await (await context.request.get(root)).json()).result.deal;
  expect(after).toEqual(before);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
