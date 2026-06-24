import { test } from '@playwright/test';

test('open GDM-SCORE-bands as multiple users', async ({ browser }) => {
  test.setTimeout(0);

  const owner = { name: 'analyst1', auth: '.auth/analyst1.json' };
  const decisionMakers = [
    { name: 'dm1', auth: '.auth/dm1.json' },
    { name: 'dm2', auth: '.auth/dm2.json' },
  ];

  const ownerContext = await browser.newContext({
    storageState: owner.auth,
    viewport: null,
  });
  const ownerPage = await ownerContext.newPage();

  await Promise.all([
    ownerPage.waitForResponse(
      (response) =>
        response.url().includes('/interactive_methods/GDM-SCORE-bands/fetch_score_bands') &&
        response.request().method() === 'POST' &&
        response.status() === 200,
      { timeout: 30_000 }
    ),
    ownerPage.goto('http://localhost:5173/interactive_methods/GDM-SCORE-bands?group=1'),
  ]);

  console.log(`Opened ${owner.name} and waited for initialization`);

  for (const user of decisionMakers) {
    const context = await browser.newContext({
      storageState: user.auth,
      viewport: null,
    });

    const page = await context.newPage();

    await page.goto(
      'http://localhost:5173/interactive_methods/GDM-SCORE-bands?group=1'
    );

    console.log(`Opened ${user.name}`);
  }

  await new Promise(() => {});
});