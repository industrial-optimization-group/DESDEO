// webui/tests/auth.setup.ts
import { chromium } from '@playwright/test';
import fs from 'fs';

const BASE_URL = 'http://localhost:5173';

const users = [
  {
    name: 'analyst1',
    password: '12345',
  },
  {
    name: 'dm1',
    password: '12345',
  },
  {
    name: 'dm2',
    password: '12345',
  },
];

async function loginAndSave(user: {
  name: string;
  password: string;
}) {
  const browser = await chromium.launch({ headless: false });

  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(BASE_URL);

  // Adjust selectors to your login form
  await page.getByLabel('Username').fill(user.name);
  await page.getByLabel('Password').fill(user.password);

  await page.getByRole('button', { name: /login/i }).click();

  // Wait until logged in
  await page.waitForLoadState('networkidle');

  fs.mkdirSync('.auth', { recursive: true });

  await context.storageState({
    path: `.auth/${user.name}.json`,
  });

  console.log(`Saved auth for ${user.name}`);

  await browser.close();
}

(async () => {
  for (const user of users) {
    await loginAndSave(user);
  }
})();