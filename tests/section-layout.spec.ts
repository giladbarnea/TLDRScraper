/// <reference lib="dom" />

import { test, expect } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import process from 'process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const SERVER_URL = 'http://127.0.0.1:5002/';

let serverProcess: ChildProcess | null = null;

async function waitForServer(url: string, timeoutMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (serverProcess && serverProcess.exitCode !== null) {
            throw new Error(`Server exited with code ${serverProcess.exitCode}`);
        }
        try {
            const response = await fetch(url, { method: 'GET' });
            if (response.ok) {
                await response.arrayBuffer();
                return;
            }
        } catch (_) {
            // swallow, retry
        }
        await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw new Error('Timed out waiting for server to start');
}

test.beforeAll(async () => {
    serverProcess = spawn(
        'uv',
        ['run', 'flask', '--app', 'serve', 'run', '--port', '5002', '--no-reload'],
        {
            cwd: PROJECT_ROOT,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: 'pipe'
        }
    );

    serverProcess.stdout?.setEncoding('utf-8');
    serverProcess.stderr?.setEncoding('utf-8');
    serverProcess.stdout?.on('data', data => {
        process.stdout.write(`[server] ${data}`);
    });
    serverProcess.stderr?.on('data', data => {
        process.stderr.write(`[server-err] ${data}`);
    });

    await waitForServer(SERVER_URL);
});

test.afterAll(async () => {
    if (!serverProcess) return;
    await new Promise(resolve => {
        const done = () => resolve(undefined);
        serverProcess?.once('exit', done);
        serverProcess?.kill('SIGINT');
    });
    serverProcess = null;
});

test('sections appear above their corresponding articles (warm start from localStorage)', async ({ page }) => {
    await page.goto(SERVER_URL);

    const startInput = page.locator('#start_date');
    const endInput = page.locator('#end_date');
    const endDateValue = await endInput.inputValue();
    const sampleDate = endDateValue || (await startInput.inputValue()) || '2024-08-01';

    await startInput.fill(sampleDate);
    await endInput.fill(sampleDate);

    // Create sample data with multiple sections
    const sampleResponse = {
        success: true,
        stats: {
            total_articles: 6,
            unique_urls: 6,
            dates_with_content: 1,
            dates_processed: 1,
            debug_logs: []
        },
        issues: [
            {
                date: sampleDate,
                category: 'TLDR Tech',
                title: 'TLDR Tech',
                slug: 'tech',
                url: 'https://example.com/issue',
                newsletter_type: 'daily',
                sections: [
                    {
                        title: 'Research',
                        order: 1,
                        emoji: '🔬'
                    },
                    {
                        title: 'AI',
                        order: 2,
                        emoji: '🤖'
                    },
                    {
                        title: 'Development',
                        order: 3,
                        emoji: '💻'
                    }
                ]
            }
        ],
        articles: [
            {
                date: sampleDate,
                url: 'https://example.com/article-research-1',
                title: 'Research Article 1 (example.com)',
                category: 'TLDR Tech',
                section_title: 'Research',
                section_order: 1,
                section_emoji: '🔬',
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-research-2',
                title: 'Research Article 2 (example.com)',
                category: 'TLDR Tech',
                section_title: 'Research',
                section_order: 1,
                section_emoji: '🔬',
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-ai-1',
                title: 'AI Article 1 (example.com)',
                category: 'TLDR Tech',
                section_title: 'AI',
                section_order: 2,
                section_emoji: '🤖',
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-ai-2',
                title: 'AI Article 2 (example.com)',
                category: 'TLDR Tech',
                section_title: 'AI',
                section_order: 2,
                section_emoji: '🤖',
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-dev-1',
                title: 'Development Article 1 (example.com)',
                category: 'TLDR Tech',
                section_title: 'Development',
                section_order: 3,
                section_emoji: '💻',
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-dev-2',
                title: 'Development Article 2 (example.com)',
                category: 'TLDR Tech',
                section_title: 'Development',
                section_order: 3,
                section_emoji: '💻',
                newsletter_type: 'daily',
                removed: false
            }
        ]
    };

    await page.route('**/api/scrape', route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(sampleResponse)
        })
    );

    // Initial scrape to populate localStorage
    const scrapeResponse = page.waitForResponse('**/api/scrape');
    await page.getByRole('button', { name: 'Scrape TLDR Newsletters' }).click();
    await scrapeResponse;

    const cards = page.locator('.article-card');
    await expect(cards).toHaveCount(6, { timeout: 15000 });

    // Wait for localStorage to be populated
    await page.waitForTimeout(1000);

    // Reload the page to trigger warm start from localStorage
    await page.reload();
    await page.waitForTimeout(1000);

    // Now check the layout - sections should be positioned correctly relative to their articles

    // Get all section titles
    const sectionTitles = page.locator('.section-title');
    await expect(sectionTitles).toHaveCount(3);

    // Get all article cards
    const allCards = page.locator('.article-card');
    await expect(allCards).toHaveCount(6);

    // Get absolute Y positions
    const researchSection = sectionTitles.nth(0);
    const aiSection = sectionTitles.nth(1);
    const devSection = sectionTitles.nth(2);

    const researchArticle1 = page.locator('.article-card[data-url="https://example.com/article-research-1"]');
    const researchArticle2 = page.locator('.article-card[data-url="https://example.com/article-research-2"]');
    const aiArticle1 = page.locator('.article-card[data-url="https://example.com/article-ai-1"]');
    const aiArticle2 = page.locator('.article-card[data-url="https://example.com/article-ai-2"]');
    const devArticle1 = page.locator('.article-card[data-url="https://example.com/article-dev-1"]');
    const devArticle2 = page.locator('.article-card[data-url="https://example.com/article-dev-2"]');

    // Get Y positions
    const researchSectionY = await researchSection.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const aiSectionY = await aiSection.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const devSectionY = await devSection.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });

    const researchArticle1Y = await researchArticle1.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const researchArticle2Y = await researchArticle2.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const aiArticle1Y = await aiArticle1.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const aiArticle2Y = await aiArticle2.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const devArticle1Y = await devArticle1.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    const devArticle2Y = await devArticle2.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });

    // Assert that section titles appear BEFORE their corresponding articles
    // Research section should be above its articles
    expect(researchSectionY).toBeLessThan(researchArticle1Y);
    expect(researchSectionY).toBeLessThan(researchArticle2Y);

    // Research articles should be above AI section
    expect(researchArticle1Y).toBeLessThan(aiSectionY);
    expect(researchArticle2Y).toBeLessThan(aiSectionY);

    // AI section should be above its articles
    expect(aiSectionY).toBeLessThan(aiArticle1Y);
    expect(aiSectionY).toBeLessThan(aiArticle2Y);

    // AI articles should be above Development section
    expect(aiArticle1Y).toBeLessThan(devSectionY);
    expect(aiArticle2Y).toBeLessThan(devSectionY);

    // Development section should be above its articles
    expect(devSectionY).toBeLessThan(devArticle1Y);
    expect(devSectionY).toBeLessThan(devArticle2Y);

    console.log('Y Positions:');
    console.log('Research Section:', researchSectionY);
    console.log('Research Article 1:', researchArticle1Y);
    console.log('Research Article 2:', researchArticle2Y);
    console.log('AI Section:', aiSectionY);
    console.log('AI Article 1:', aiArticle1Y);
    console.log('AI Article 2:', aiArticle2Y);
    console.log('Development Section:', devSectionY);
    console.log('Development Article 1:', devArticle1Y);
    console.log('Development Article 2:', devArticle2Y);
});
