// Shared Playwright fixture: tests must not hit the network. The app loads Google Fonts from
// index.html; blocking them here keeps every spec offline (the page falls back to system fonts).
import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.abort());
    await use(context);
  },
});

export { expect };
