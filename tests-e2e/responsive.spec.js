// Responsive verification suite — adapted from the engineering-webapp-skills
// responsive-e2e-harness pattern (see HealthForecast's tests/responsive.spec.js
// for the original this was modelled on).
//
// 1) No horizontal overflow on any route at any width (portrait first).
// 2) Console-clean at phone widths.
// 3) Interactive elements meet the 24px WCAG 2.5.8 AA hit-area floor.
// 4) Screenshots for manual review at a representative width subset.
//
// The backend is not required for most routes — Extraction/Compare/Boq/
// Pricing render their "no run selected" empty state without one, which
// still exercises the layout system, matching the original harness's own
// approach.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const WIDTHS = [320, 360, 390, 414, 768, 1024, 1440, 1920];
const HEIGHT = { 320: 693, 360: 800, 390: 844, 414: 896, 640: 800, 768: 1024, 1024: 1366, 1440: 900, 1920: 1080 };
const SHOT_WIDTHS = [320, 390, 768, 1440];

// login/welcome/upload/extraction/compare/boq/pricing all sit behind the
// demo-login gate (App.jsx's isAuthed check) — authed via addInitScript
// below rather than clicking through Login on every single test.
const ROUTES = ['landing', 'login', 'welcome', 'upload', 'extraction', 'compare', 'boq', 'pricing', 'audit'];
const AUTH_KEY = 'afriplan_demo_authed';

fs.mkdirSync('screenshots', { recursive: true });

async function openRoute(page, route, width) {
  await page.addInitScript((key) => localStorage.setItem(key, '1'), AUTH_KEY);
  await page.setViewportSize({ width, height: HEIGHT[width] });
  await page.goto(`/#${route}`);
  await page.waitForTimeout(800);
}

for (const route of ROUTES) {
  for (const width of WIDTHS) {
    test(`${route} @ ${width}px — no horizontal overflow`, async ({ page }) => {
      await openRoute(page, route, width);
      const m = await page.evaluate(() => ({
        sw: document.documentElement.scrollWidth,
        cw: document.documentElement.clientWidth,
      }));
      expect(m.sw, `scrollWidth ${m.sw}px exceeds viewport ${m.cw}px`).toBeLessThanOrEqual(m.cw + 1);
      if (SHOT_WIDTHS.includes(width)) {
        await page.screenshot({ path: `screenshots/${route}-${width}.png`, fullPage: true });
      }
    });
  }
}

const IGNORED_CONSOLE = /Failed to load resource|net::ERR|favicon|load failed/i;
const CONSOLE_WIDTHS = [320, 390];

for (const route of ROUTES) {
  for (const width of CONSOLE_WIDTHS) {
    test(`${route} @ ${width}px — console clean`, async ({ page }) => {
      const errors = [];
      page.on('console', (m) => {
        if (m.type() === 'error' && !IGNORED_CONSOLE.test(m.text())) errors.push(m.text());
      });
      page.on('pageerror', (e) => errors.push(String(e)));
      await openRoute(page, route, width);
      expect(errors, `console errors: ${errors.join(' | ')}`).toHaveLength(0);
    });
  }
}

for (const route of ROUTES) {
  for (const width of [320, 390]) {
    test(`${route} @ ${width}px — hit areas meet the 24px AA floor, no overlaps`, async ({ page }) => {
      await openRoute(page, route, width);
      const r = await page.evaluate(() => {
        const vw = window.innerWidth, vh = window.innerHeight;
        const visible = (b) => b.width > 0 && b.height > 0 && b.right > 0 && b.left < vw && b.bottom > 0 && b.top < vh;
        const small = [];
        let under44 = 0;
        const boxes = [];
        document.querySelectorAll('button, a, [role="button"], input, select').forEach((el) => {
          const b = el.getBoundingClientRect();
          if (!visible(b) || el.offsetParent === null) return;
          if (b.width < 24 || b.height < 24) small.push(`${(el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 24)} ${Math.round(b.width)}x${Math.round(b.height)}`);
          else if (b.width < 44 || b.height < 44) under44 += 1;
          boxes.push(b);
        });
        let overlaps = 0;
        for (let i = 0; i < boxes.length; i++) {
          for (let j = i + 1; j < boxes.length; j++) {
            const a = boxes[i], b = boxes[j];
            const xo = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const yo = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            if (xo > 2 && yo > 2) overlaps += 1;
          }
        }
        return { small, overlaps, under44 };
      });
      expect(r.small, `hit areas under the 24px AA floor: ${r.small.join('; ')}`).toHaveLength(0);
      expect(r.overlaps, 'overlapping clickable bounding boxes').toBe(0);
    });
  }
}

// 200% browser zoom approximation: a 640px viewport lays out like 1280px at
// 200% zoom. True browser-zoom behaviour on a real device stays UNVERIFIED.
for (const route of ['landing', 'upload', 'boq', 'pricing']) {
  test(`${route} @ 640px (zoom 200% approximation) — no horizontal overflow`, async ({ page }) => {
    await openRoute(page, route, 640);
    const m = await page.evaluate(() => ({
      sw: document.documentElement.scrollWidth,
      cw: document.documentElement.clientWidth,
    }));
    expect(m.sw).toBeLessThanOrEqual(m.cw + 1);
  });
}

// Plan C rule: Upload must never fire a heavy compute call on page load —
// only after the user picks a file and clicks Run.
test('upload @ 390px — no run/compare POST on page load', async ({ page }) => {
  const heavy = [];
  page.on('request', (r) => {
    const url = r.url();
    if (url.includes('/api/runs') || url.includes('/api/compare')) {
      if (r.method() === 'POST') heavy.push(`${r.method()} ${url}`);
    }
  });
  await openRoute(page, 'upload', 390);
  expect(heavy, `heavy call(s) fired on page load: ${heavy.join(', ')}`).toHaveLength(0);
});
