import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
async function enter(page: import("@playwright/test").Page, name: string) {
  await page.goto("/");
  await page.locator("#identity").selectOption("demo_id_owner");
  await page.getByRole("button", { name: "Enter demo", exact: true }).click();
  await page
    .locator("article")
    .filter({ hasText: name })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await expect(
    page.getByRole("button", { name: "Recalculate analysis" }),
  ).toBeVisible();
}
test("offline Calendar shows delivered, conflict resolution and revocation from persisted state", async ({
  page,
  context,
}) => {
  await enter(page, "Synthetic coffee · negotiation");
  await page
    .getByRole("button", { name: "Readiness & timeline", exact: true })
    .click();
  const milestoneForm = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Record an external milestone" }),
  });
  await milestoneForm
    .getByLabel("Local date (Asia/Jakarta)")
    .fill("2026-11-01");
  await milestoneForm
    .getByLabel("Reviewed supporting evidence")
    .selectOption({ index: 1 });
  await milestoneForm
    .getByRole("button", { name: "Record milestone", exact: true })
    .click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  const panel = page
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: "Optional calendar" }) });
  await panel.locator("summary").click();
  await expect(
    panel.getByText("SYNTHETIC DEMO · no Google requests"),
  ).toBeVisible();
  await panel
    .getByRole("button", { name: "Connect demo calendar", exact: true })
    .click();
  await expect(
    panel.getByText("Connection status: connected", { exact: false }),
  ).toBeVisible();
  const connection = await panel
    .getByRole("combobox", { name: "Calendar connection", exact: true })
    .inputValue();
  const checkbox = panel
    .getByRole("group", { name: "Milestones to project" })
    .getByRole("checkbox")
    .first();
  await checkbox.check();
  const label = await checkbox.locator("..").innerText();
  const milestone = label.split(" · ").at(-1)!.trim();
  await panel
    .getByRole("button", { name: "Preview projection", exact: true })
    .click();
  await expect(
    panel.getByText("Projection hash:", { exact: false }),
  ).toBeVisible();
  await panel
    .getByRole("button", { name: "Approve this projection hash" })
    .click();
  await expect(
    panel.getByRole("button", {
      name: "Run approved demo projection",
    }),
  ).toBeEnabled();
  await panel
    .getByRole("button", { name: "Run approved demo projection" })
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "partial",
    { timeout: 20000 },
  );
  await expect(async () => {
    await panel
      .getByRole("button", { name: "Refresh projection status" })
      .click();
    await expect(panel.getByText(/projection status: delivered/)).toBeVisible();
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
  await panel
    .getByRole("button", { name: "Refresh projection status" })
    .click();
  await expect(panel.getByText(/projection status: conflict/)).toBeVisible();
  await panel.getByRole("button", { name: "Keep external changes" }).click();
  await expect(
    panel.getByText(/projection status: external_retained/),
  ).toBeVisible();
  await panel.getByRole("button", { name: "Revoke this connection" }).click();
  await expect(
    panel.getByText("Connection status: revoked", { exact: false }),
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
    .getByRole("button", { name: "Documents & terms", exact: true })
    .click();
  const panel = page.locator("details").filter({
    has: page.locator("summary", {
      hasText: "Research public sources for your product & route",
    }),
  });
  await panel.locator("summary").click();
  await panel.getByRole("button", { name: "Preview research usage" }).click();
  await expect(panel.getByRole("status")).toContainText(
    "0 research allowance units",
  );
  await panel
    .getByRole("button", { name: "Start research within these limits" })
    .click();
  await expect(page.getByTestId("job-state")).toHaveAttribute(
    "data-status",
    "succeeded",
    { timeout: 20000 },
  );
  await page
    .getByTestId("job-state")
    .getByText("Source & provider access trail")
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
    .getByRole("button", { name: "Settlement & closure", exact: true })
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
      hasText: "Record pending payment evidence",
    }),
  });
  await form.locator("summary").click();
  await form
    .getByRole("combobox", { name: "Obligation", exact: true })
    .selectOption(obligation.id);
  await form.getByLabel("Amount received", { exact: true }).fill(amount);
  await form.getByLabel("Value date", { exact: true }).fill("2026-10-15");
  await form.getByRole("button", { name: "Save pending evidence" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  const review = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Verify & correct payment evidence",
    }),
  });
  let receipt = review
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: amount }) })
    .last();
  await receipt.locator("summary").click();
  await receipt
    .getByLabel("Known settlement time (UTC, optional)")
    .fill("2026-10-15T12:00");
  await receipt
    .getByLabel("Reviewed supporting evidence")
    .selectOption({ index: 1 });
  await receipt
    .getByLabel("Review reason / notes")
    .fill("Offline evaluator verified seller transfer");
  await receipt.getByRole("button", { name: "Save payment review" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  receipt = review
    .locator("details")
    .filter({ has: page.locator("summary", { hasText: amount }) })
    .last();
  await expect(receipt.locator("summary")).toContainText("Verified");
  if (!(await receipt.getAttribute("open")))
    await receipt.locator("summary").click();
  await receipt
    .getByLabel("Reviewed supporting evidence")
    .selectOption({ index: 1 });
  await receipt
    .getByLabel("Review reason / notes")
    .fill(
      "Reverse the synthetic evaluator transfer and restore the checkpoint",
    );
  await receipt.getByRole("button", { name: "Save payment review" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
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
    page.getByRole("button", { name: "Enter demo", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Your workspaces" }),
  ).toBeVisible();
  const open = page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Open workspace" });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Recalculate analysis" }),
  ).toBeVisible();
  const economics = page.getByRole("button", {
    name: "Cost & margin",
    exact: true,
  });
  await economics.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Declared costs" }),
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
    has: page.locator("summary", {
      hasText: "Owner constraints & preferences",
    }),
  });
  await panel.locator("summary").click();
  await panel
    .getByRole("combobox", { name: "Reviewed evidence", exact: true })
    .selectOption({ index: 1 });
  await panel
    .getByLabel("Reason for changing owner constraints")
    .fill("Review a synthetic updated bank opening balance");
  await panel
    .getByLabel("Commitments outside this deal", { exact: true })
    .fill("");
  await panel.getByRole("button", { name: "Save owner constraints" }).click();
  await expect(panel.getByRole("alert")).toContainText("Complete the balance");
  const unchanged = (await (await context.request.get(path)).json()).result
    .deal;
  expect(unchanged.revision).toBe(before.revision);
  await panel
    .getByLabel("Commitments outside this deal", { exact: true })
    .fill(before.constraints.cash_snapshot.committed_elsewhere.amount);
  const changed =
    before.constraints.cash_snapshot.available.amount === "50000001"
      ? "50000002"
      : "50000001";
  await panel.getByLabel("Available balance", { exact: true }).fill(changed);
  await panel.getByRole("button", { name: "Save owner constraints" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
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
    .getByLabel("Available balance", { exact: true })
    .fill(before.constraints.cash_snapshot.available.amount);
  await panel
    .getByRole("combobox", { name: "Reviewed evidence", exact: true })
    .selectOption({ index: 1 });
  await panel
    .getByLabel("Reason for changing owner constraints")
    .fill("Restore the evaluator opening amount");
  await panel.getByRole("button", { name: "Save owner constraints" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();
  expect(
    (await (await context.request.get(path)).json()).result.deal.constraints
      .cash_snapshot.available.amount,
  ).toBe(before.constraints.cash_snapshot.available.amount);
});
