import { test, expect } from "@playwright/test";

test("Google return preserves Strict session authentication and consumes state once", async ({
  page,
  context,
  baseURL,
}) => {
  const origin = new URL(baseURL!).origin;
  const login = await context.request.post(origin + "/api/session", {
    headers: { Origin: origin },
    data: { user_id: "demo_id_owner" },
  });
  expect(login.ok()).toBe(true);
  const authorization = await context.request.post(
    origin + "/api/gateway/calendar/connections",
    {
      headers: { Origin: origin },
      data: { redirect_uri: origin + "/oauth/calendar/callback" },
    },
  );
  expect(authorization.ok()).toBe(true);
  const state = (await authorization.json()).result.state;
  const callback =
    origin +
    "/oauth/calendar/callback?" +
    new URLSearchParams({ code: "offline-demo", state });
  // Different site, same local test server: no Google calls or mocked API replies.
  const otherSite = new URL(origin);
  otherSite.hostname =
    otherSite.hostname === "localhost" ? "127.0.0.1" : "localhost";
  await page.goto(otherSite.toString());
  await page.evaluate((url) => window.location.assign(url), callback);
  await expect(page.getByRole("status")).toContainText("Google connected");
  expect(new URL(page.url()).search).toBe("");
  await expect(page.locator('meta[name="referrer"]')).toHaveAttribute(
    "content",
    "no-referrer",
  );
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
  const connections = await context.request.get(
    origin + "/api/gateway/calendar/connections",
  );
  expect(
    (await connections.json()).result.items.some(
      (c: { status: string; calendar_id: string | null }) =>
        c.status === "connected" && c.calendar_id === null,
    ),
  ).toBe(true);
  await page.goto(callback);
  await expect(page.getByRole("status")).toContainText(
    "The Google connection failed",
  );
});

test("Google cancellation and malformed callbacks never submit an exchange", async ({
  page,
}) => {
  let exchanges = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/gateway/calendar/callback")) exchanges++;
  });
  await page.goto("/oauth/calendar/callback?error=access_denied&state=unused");
  await expect(page.getByRole("status")).toContainText("cancelled or denied");
  expect(new URL(page.url()).search).toBe("");
  await page.goto("/oauth/calendar/callback?code=one&code=two&state=unused");
  await expect(page.getByRole("status")).toContainText(
    "Invalid Google callback",
  );
  expect(exchanges).toBe(0);
});

test("Google callback without a session requests a fresh login", async ({
  page,
}) => {
  await page.goto("/oauth/calendar/callback?code=offline-demo&state=unowned");
  await expect(page.getByRole("status")).toContainText("Your session expired");
  expect(new URL(page.url()).search).toBe("");
});
