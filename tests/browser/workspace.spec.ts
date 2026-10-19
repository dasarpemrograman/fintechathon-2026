import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";
test("funding dates preserve local dates and declared timezones", async ({
  page,
  context,
  baseURL,
}) => {
  const origin = new URL(baseURL!).origin;
  const marker = "Local-date browser regression " + randomUUID();
  const login = await context.request.post("/api/session", {
    headers: { Origin: origin },
    data: { user_id: "demo_id_owner" },
  });
  expect(login.ok()).toBe(true);
  const workspace = await (
    await context.request.get("/api/gateway/workspaces/demo_stage_negotiation")
  ).json();
  const root = "/api/gateway/deals/" + workspace.result.deal_id;
  const deal = await (await context.request.get(root)).json();
  const response = await context.request.post(root + "/funding-options", {
    headers: { Origin: origin },
    data: {
      expected_revision: deal.result.deal.revision,
      fundingOption: {
        product_id: null,
        fit: "needs_information",
        fit_reasons: [marker],
        failed_predicates: [],
        unknown_predicates: ["Hypothetical facility"],
        draw: { amount: "10.00", currency: "IDR" },
        earliest_draw_milestone_id: null,
        schedule: [
          {
            kind: "loan_draw",
            amount: { amount: "10.00", currency: "IDR" },
            schedule: {
              kind: "fixed",
              due: { date: "2026-10-20", timezone: "Pacific/Kiritimati" },
            },
            status: "proposed",
            evidence_ids: [],
          },
          {
            kind: "principal_repayment",
            amount: { amount: "10.00", currency: "IDR" },
            schedule: {
              kind: "fixed",
              due: {
                instant: "2026-11-21T01:00:00Z",
                timezone: "America/Los_Angeles",
              },
            },
            status: "proposed",
            evidence_ids: [],
          },
        ],
        assumptions: [],
        status: "proposed",
        external_facility_evidence_ids: [],
      },
    },
  });
  expect(response.ok()).toBe(true);
  await page.goto("/");
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page
    .getByRole("button", { name: "Scenarios & funding", exact: true })
    .click();
  const option = page.locator("article").filter({ hasText: marker });
  await expect(option).toHaveCount(1);
  await expect(
    option.getByText("2026-10-20 · Pacific/Kiritimati", { exact: true }),
  ).toBeVisible();
  const instant = await page.evaluate(() =>
    new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "America/Los_Angeles",
    }).format(new Date("2026-11-21T01:00:00Z")),
  );
  await expect(
    option.getByText(instant + " · America/Los_Angeles", { exact: true }),
  ).toBeVisible();
  await expect(
    option.getByText("Relative to an event", { exact: true }),
  ).toHaveCount(0);
});

test("seeded database journey uses the browser, API and worker", async ({
  page,
  context,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (e) => failures.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Enter demo", exact: true }),
  ).toBeVisible();
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your workspaces" }),
  ).toBeVisible();
  const cookies = await context.cookies();
  const session = cookies.find((c) => c.name === "fincathon_session");
  expect(session?.httpOnly).toBe(true);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  const card = page
    .locator("article")
    .filter({ hasText: "Coffee" })
    .filter({ hasText: "Deal" })
    .first();
  await card.getByRole("button", { name: "Open workspace" }).click();
  await expect(
    page.getByRole("button", { name: "Recalculate analysis" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Recalculate analysis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page
    .getByRole("button", { name: "Economics & cash", exact: true })
    .click();
  await expect(
    page.getByText("IDR 26000000.00", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("-52000000.00", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Evidence & documents", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sources & excerpts" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.getByRole("button", { name: "Recalculate analysis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your workspaces" }),
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

test("browser logout revokes its server token before clearing the HttpOnly cookie", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your workspaces" }),
  ).toBeVisible();
  const session = (await context.cookies()).find(
    (c) => c.name === "fincathon_session",
  )!;
  expect(session.httpOnly).toBe(true);
  expect(session.sameSite).toBe("Strict");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to your organization" }),
  ).toBeVisible();
  expect((await context.cookies()).some((c) => c.name === session.name)).toBe(
    false,
  );
  const rejected = await context.request.get(
    "http://127.0.0.1:8000/v2/auth/session",
    {
      headers: { Authorization: "Bearer " + session.value },
    },
  );
  expect(rejected.status()).toBe(401);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Sign in to your organization" }),
  ).toBeVisible();
});

test("funding comparison and analysis-bound draft use real worker outputs", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Coffee" })
    .filter({ hasText: "Deal" })
    .first()
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page.getByRole("button", { name: "Recalculate analysis" }).click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page
    .getByRole("button", { name: "Scenarios & funding", exact: true })
    .click();
  await page.getByRole("button", { name: "Find funding options" }).click();
  await expect(
    page
      .getByRole("button", { name: "Calculate this funding scenario" })
      .first(),
  ).toBeVisible({ timeout: 20000 });
  await page
    .getByRole("button", { name: "Calculate this funding scenario" })
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
    .getByRole("button", { name: "Economics & cash", exact: true })
    .click();
  await expect(
    page.getByText("IDR 23800000.00", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("7000000.00", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Drafts & approvals", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create a draft from analysis" })
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    {
      timeout: 20000,
    },
  );
  await page.locator("details").last().locator("summary").click();
  await expect(
    page.getByRole("link", { name: "Download draft" }).last(),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download draft" }).last().click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/artifact/);
  const stream = await file.createReadStream();
  let text = "";
  for await (const part of stream!) text += part.toString();
  expect(text).toContain("160000000");
  expect(text).toContain("DRAFT");
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
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · blocked goods" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page
    .getByRole("button", { name: "Readiness & timeline", exact: true })
    .click();
  const section = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Goods inspection & corrections",
      exact: true,
    }),
  });
  await section.locator("select").first().selectOption("ready");
  await section.getByLabel("Measured quantity (kg)").fill("10");
  await section
    .getByLabel("Reviewed supporting evidence")
    .selectOption({ index: 1 });
  await section
    .getByLabel("Review reason / notes")
    .fill("Synthetic measured inspection for browser acceptance");
  await section.getByRole("button", { name: "Save goods inspection" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  await expect(
    page.getByText("GOODS_CONFORMITY", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Verify opening balance sources" }),
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
    .getByLabel("Review reason / notes")
    .fill("Restore the versioned nonconforming demonstration checkpoint");
  await section.getByRole("button", { name: "Save goods inspection" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
});

test("edits survive reload and the completed checkpoint reconciles through HTTP", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  const description = page.getByLabel("Product description", { exact: true });
  const original = await description.inputValue();
  const changed = original + " · browser persistence";
  await description.fill(changed);
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  await page.reload();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await expect(description).toHaveValue(changed);
  await description.fill(original);
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "← All workspaces" }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · reconciling" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page
    .getByRole("button", { name: "Settlement & closure", exact: true })
    .click();
  await expect(
    page.getByText("Buyer payment and internal closure are separate states.", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Run reconciliation", exact: true })
    .click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluate internal closure", exact: true })
    .click();
  await expect(
    page.getByText("Closure is still blocked. Review the gate conditions.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "← All workspaces" }).click();
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · closed" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page
    .getByRole("button", { name: "Settlement & closure", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Run reconciliation", exact: true })
    .click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Evaluate internal closure", exact: true })
    .click();
  await expect(
    page.getByText(
      "The deal is closed after all prerequisites have been met.",
      {
        exact: true,
      },
    ),
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
