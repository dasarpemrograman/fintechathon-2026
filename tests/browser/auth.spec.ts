import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";

function account(input: object) {
  const command =
    process.env.FINCATHON_BROWSER_COMPOSE === "1"
      ? "docker"
      : ".venv/bin/python";
  const script = "tests/browser/support_account.py";
  const args =
    command === "docker"
      ? [
          "compose",
          "-f",
          "compose.yaml",
          "-f",
          "compose.demo.yaml",
          "exec",
          "-T",
          "api",
          "python",
          script,
        ]
      : [script];
  return execFileSync(command, args, {
    input: JSON.stringify(input),
    encoding: "utf8",
    timeout: 20000,
  });
}

test("normal account login and organization selection persist, then logout revokes access", async ({
  page,
  context,
}) => {
  const email = randomUUID() + "@example.test";
  const password = randomUUID();
  const identity = JSON.parse(
    account({ action: "provision", email, password }),
  );
  try {
    await page.goto("/");
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Your workspaces" }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Organization", exact: true })
      .selectOption(identity.organization_id);
    await expect(async () => {
      const session = await context.request.get("/api/gateway/auth/session");
      expect((await session.json()).result.organization_id).toBe(
        identity.organization_id,
      );
    }).toPass();
    const created = await context.request.post("/api/gateway/workspaces", {
      headers: { Origin: new URL(page.url()).origin },
      data: {
        mode: "sandbox",
        business_profile: "reseller",
        reporting_currency: "EUR",
        owner_timezone: "UTC",
        product: { description: "Private first-organization workspace" },
      },
    });
    expect(created.status()).toBe(201);
    await page.reload();
    await expect(
      page.getByRole("heading", {
        name: "Private first-organization workspace",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByText("Usage & plans · team", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("combobox", { name: "Organization", exact: true })
      .selectOption(identity.second_organization_id);
    await expect(async () => {
      const session = await context.request.get("/api/gateway/auth/session");
      expect((await session.json()).result.organization_id).toBe(
        identity.second_organization_id,
      );
    }).toPass();
    await expect(
      page.getByRole("heading", {
        name: "Private first-organization workspace",
        exact: true,
      }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Usage & plans · free_sandbox", { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("combobox", { name: "Organization", exact: true }),
    ).toHaveValue(identity.second_organization_id);
    const session = (await context.cookies()).find(
      (cookie) => cookie.name === "fincathon_session",
    )!;
    expect(session.httpOnly).toBe(true);
    expect(await page.evaluate(() => document.cookie)).not.toContain(
      session.value,
    );
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Sign in to your organization" }),
    ).toBeVisible();
    expect(
      (await context.cookies()).some((cookie) => cookie.name === session.name),
    ).toBe(false);
    const rejected = await context.request.get(
      "http://127.0.0.1:8000/v2/auth/session",
      { headers: { Authorization: "Bearer " + session.value } },
    );
    expect(rejected.status()).toBe(401);
  } finally {
    account({ action: "cleanup", ...identity });
  }
});
