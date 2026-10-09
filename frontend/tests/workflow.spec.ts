import { test, expect } from "@playwright/test";

test("offline draft survives reload, syncs once, and only review changes coverage", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Every street counts." }),
  ).toBeVisible();
  await expect(
    page.getByText("1 survey segments", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".map-shell")).toHaveAttribute(
    "data-ready",
    "true",
  );
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await page.getByRole("button", { name: "Start a survey" }).click();
  await page.getByLabel("Street segment").selectOption("test-segment");
  await page.getByLabel("Surveyor alias").fill("synthetic-surveyor");
  await page.getByLabel("I consent to storing").check();
  await context.setOffline(true);
  await page.getByRole("button", { name: "Save draft on this device" }).click();
  await expect(
    page.getByText("Street inspection", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Every street counts." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Field notebook", exact: true })
    .click();
  await expect(
    page.getByText("Street inspection", { exact: true }),
  ).toBeVisible();
  await context.setOffline(false);
  await page.getByRole("button", { name: "Access", exact: true }).click();
  await page.getByLabel("Access key").fill("e2e-survey");
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await page
    .getByRole("button", { name: "Sync for review", exact: true })
    .click();
  await expect(page.getByText("1 draft synced for review.")).toBeVisible();
  await expect(page.getByText("Notebook is clear")).toBeVisible();
  await page.getByRole("button", { name: "Back to map" }).click();
  await expect(page.getByText("0%", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Access", exact: true }).click();
  await page.getByLabel("Access key").fill("e2e-review");
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await page
    .getByRole("button", { name: "Evidence review", exact: true })
    .click();
  await page.getByRole("button", { name: "Load evidence" }).click();
  await page
    .getByLabel("Review reason")
    .fill("Synthetic evidence validated for browser test only");
  await page.getByRole("button", { name: "Approve evidence" }).click();
  await expect(
    page.getByText("Review recorded in the audit log."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back to map" }).click();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
});

test("mobile layout fits and reports retain uncertainty", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Every street counts." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Pilot report", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Narkelbagan field report" }),
  ).toBeVisible();
  await expect(
    page.getByText(/No online inventory can establish/),
  ).toBeVisible();
  const data = await (await page.request.get("/api/export")).json();
  expect(JSON.stringify(data)).not.toContain("synthetic-surveyor");
});

test("GPS photo observation stays private until reviewed", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: 22.491,
    longitude: 88.3675,
    accuracy: 5,
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start a survey" }).click();
  await page.getByRole("button", { name: "Record a bin", exact: true }).click();
  await page.getByLabel("Street segment").selectOption("test-segment");
  await page.getByLabel("Surveyor alias").fill("photo-fixture");
  await page.getByRole("button", { name: "Locate me" }).click();
  await expect(page.getByText("Location captured")).toBeVisible();
  await page
    .getByLabel("Photograph", { exact: true })
    .setInputFiles({
      name: "test-only.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII=",
        "base64",
      ),
    });
  await page.getByLabel("I consent to storing").check();
  await page.getByRole("button", { name: "Save draft on this device" }).click();
  await page.getByRole("button", { name: "Access", exact: true }).click();
  await page.getByLabel("Access key").fill("e2e-survey");
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await page
    .getByRole("button", { name: "Sync for review", exact: true })
    .click();
  await expect(page.getByText("1 draft synced for review.")).toBeVisible();
  expect(
    (await (await page.request.get("/api/bins")).json()).features,
  ).toHaveLength(0);
  await page.getByRole("button", { name: "Access", exact: true }).click();
  await page.getByLabel("Access key").fill("e2e-review");
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await page
    .getByRole("button", { name: "Evidence review", exact: true })
    .click();
  await page.getByRole("button", { name: "Load evidence" }).click();
  await expect(page.getByAltText("Submitted bin evidence")).toBeVisible();
  await page
    .getByLabel("Review reason")
    .fill("Reviewed test-only GPS and image");
  await page.getByRole("button", { name: "Approve evidence" }).click();
  await expect(
    page.getByText("Review recorded in the audit log."),
  ).toBeVisible();
  expect(
    (await (await page.request.get("/api/bins")).json()).features,
  ).toHaveLength(1);
});
