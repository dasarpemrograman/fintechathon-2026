import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("workspace history compares immutable revisions, isolates audit, and retains archived exports", async ({
  page,
  context,
  baseURL,
}) => {
  const origin = new URL(baseURL!).origin;
  const marker = "History browser " + randomUUID();
  const login = await context.request.post("/api/session", {
    headers: { Origin: origin },
    data: { user_id: "demo_id_owner" },
  });
  expect(login.ok()).toBe(true);
  async function create(description: string) {
    const response = await context.request.post("/api/gateway/workspaces", {
      headers: { Origin: origin },
      data: {
        mode: "sandbox",
        business_profile: "producer",
        reporting_currency: "EUR",
        owner_timezone: "Africa/Nairobi",
        product: { description },
      },
    });
    expect(response.status()).toBe(201);
    return (await response.json()).result;
  }
  const original = await create(marker + " original");
  const unrelated = await create(marker + " unrelated");
  const root = "/api/gateway/workspaces/" + original.id;
  const update = await context.request.patch(root + "/facts", {
    headers: { Origin: origin },
    data: {
      expected_revision: original.revision,
      patches: [
        {
          op: "replace",
          path: "/product",
          value: { description: marker + " revised" },
          reason: "Review source correction",
          evidence_ids: [],
          agreement_required_from: [],
        },
      ],
    },
  });
  expect(update.ok()).toBe(true);
  const unrelatedAudit = (
    await (
      await context.request.get(
        "/api/gateway/audit?workspace_id=" + unrelated.id,
      )
    ).json()
  ).result.items;
  await page.goto("/");
  while (
    await page.getByRole("button", { name: "Load more workspaces" }).isVisible()
  ) {
    const count = await page.locator("article").count();
    const [response] = await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes("/api/gateway/workspaces?"),
      ),
      page.getByRole("button", { name: "Load more workspaces" }).click(),
    ]);
    const items = (await response.json()).result.items;
    await expect(page.locator("article")).toHaveCount(count + items.length);
  }
  await page
    .locator("article")
    .filter({ hasText: marker + " revised" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page.getByRole("button", { name: "History", exact: true }).click();
  await page
    .getByRole("button", { name: "Compare revisions exploration" })
    .click();
  const comparison = page.getByLabel("Revision comparison exploration");
  await expect(
    comparison.getByText(marker + " original", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    comparison.getByText(marker + " revised", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    page.getByText(unrelatedAudit[0].request_id, { exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("checkbox", {
      name: "I have reviewed this archival action.",
    })
    .check();
  await page
    .getByRole("button", { name: "Archive workspace", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Reactivate", exact: true }),
  ).toBeVisible();
  expect((await (await context.request.get(root)).json()).result.archived).toBe(
    true,
  );
  const archived = (await (await context.request.get(root)).json()).result;
  const refused = await context.request.patch(root + "/facts", {
    headers: { Origin: origin },
    data: {
      expected_revision: archived.revision,
      patches: [
        {
          op: "replace",
          path: "/product",
          value: { description: "Must not overwrite archived facts" },
          reason: "Archived mutation check",
          evidence_ids: [],
          agreement_required_from: [],
        },
      ],
    },
  });
  expect(refused.status()).toBe(409);
  expect((await refused.json()).code).toBe("ARCHIVED_READ_ONLY");
  const history = await context.request.get(root + "/revisions/1");
  expect((await history.json()).result).toEqual(original);
  const exported = await context.request.get(root + "/export");
  expect(exported.ok()).toBe(true);
  expect((await exported.json()).snapshot.archived).toBe(true);
  await page
    .getByRole("checkbox", {
      name: "I have reviewed this reactivation action.",
    })
    .check();
  await page.getByRole("button", { name: "Reactivate", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Archive workspace", exact: true }),
  ).toBeVisible();
  expect((await (await context.request.get(root)).json()).result.archived).toBe(
    false,
  );
});

test("deal history retains separate workspace and transaction revisions", async ({
  page,
  context,
  baseURL,
}) => {
  const origin = new URL(baseURL!).origin;
  const login = await context.request.post("/api/session", {
    headers: { Origin: origin },
    data: { user_id: "demo_id_owner" },
  });
  expect(login.ok()).toBe(true);
  await page.goto("/");
  await page
    .locator("article")
    .filter({ hasText: "Synthetic coffee · negotiation" })
    .getByRole("button", { name: "Open workspace" })
    .click();
  await page.getByRole("button", { name: "History", exact: true }).click();
  const workspace = page.getByRole("region", {
    name: "Revision history workspace",
    exact: true,
  });
  const deal = page.getByRole("region", {
    name: "Revision history deal",
    exact: true,
  });
  await expect(
    workspace.getByRole("combobox", {
      name: "Earlier revision workspace",
      exact: true,
    }),
  ).toBeVisible();
  await deal
    .getByRole("button", { name: "Compare revisions deal", exact: true })
    .click();
  await expect(page.getByLabel("Revision comparison deal")).toBeVisible();
  await deal
    .getByText(/^Full snapshot deal, revision/)
    .first()
    .click();
  await expect(
    deal.getByText('"line_items":', { exact: false }).first(),
  ).toBeVisible();
});
