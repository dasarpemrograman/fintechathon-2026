import { test, expect } from "@playwright/test";

test("English sign-in supports keyboard focus and readable primary actions", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page).toHaveTitle("ALLExport · Export workspace");
  await expect(
    page.getByRole("heading", { name: "Sign in to your organization" }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  const contrast = await page
    .getByRole("button", { name: "Sign in", exact: true })
    .evaluate((button) => {
      const style = getComputedStyle(button);
      const luminance = (color: string) => {
        const values = color
          .match(/[\d.]+/g)!
          .slice(0, 3)
          .map((value) => Number(value) / 255)
          .map((value) =>
            value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
          );
        return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
      };
      const a = luminance(style.color),
        b = luminance(style.backgroundColor);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    });
  expect(contrast).toBeGreaterThanOrEqual(4.5);
  expect(errors).toEqual([]);
});

test("portfolio search, filters, and section navigation use real loaded workspaces", async ({
  page,
  context,
  baseURL,
}) => {
  const login = await context.request.post("/api/session", {
    headers: { Origin: new URL(baseURL!).origin },
    data: { user_id: "demo_id_owner" },
  });
  expect(login.ok()).toBe(true);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your workspaces", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".workspace-card").first()).toBeVisible();
  const count = await page.locator(".workspace-card").count();
  const search = page.getByRole("searchbox", {
    name: "Search loaded workspaces",
  });
  await search.fill("NO-SUCH-PRODUCT-FOR-DESIGN-TEST");
  await expect(
    page.getByRole("heading", { name: "No matching workspaces" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await expect(page.locator(".workspace-card")).toHaveCount(count);
  await page.getByRole("button", { name: "Deals", exact: true }).click();
  const cards = page.locator(".workspace-card");
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThan(0);
  for (const card of await cards.all())
    await expect(card.locator(".workspace-badges .tag")).toHaveText("Deal");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Usage & plans" })
    .click();
  await expect(
    page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("button", { name: "Usage & plans" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#usage")).toBeInViewport();
});

for (const width of [320, 390, 768, 1440]) {
  test(`workspace navigation and English draft defaults fit a ${width}px viewport`, async ({
    page,
    context,
    baseURL,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await context.request.post("/api/session", {
      headers: { Origin: new URL(baseURL!).origin },
      data: { user_id: "demo_id_owner" },
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Your workspaces" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page
      .locator(".workspace-card")
      .filter({ hasText: "Synthetic coffee · negotiation" })
      .getByRole("button", { name: "Open workspace" })
      .click();
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    for (const section of [
      "Deal overview",
      "Cost & margin",
      "Cash timeline",
      "Calendar",
      "Scenarios",
      "Documents & terms",
      "Negotiation brief",
      "History",
    ]) {
      const button = page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("button", { name: section, exact: true });
      await button.click();
      await expect(button).toHaveAttribute("aria-current", "page");
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      if (section === "Negotiation brief")
        await expect(
          page.getByRole("combobox", { name: "Draft language", exact: true }),
        ).toHaveValue("en");
    }
    expect(errors).toEqual([]);
  });
}
