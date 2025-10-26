/// <reference lib="dom" />

import { test, expect } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import process from 'process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const SERVER_URL = 'http://127.0.0.1:5001/';

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
        ['run', 'flask', '--app', 'serve', 'run', '--port', '5001', '--no-reload'],
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

test('removed card moves to bottom and restores to original position', async ({ page }) => {
    await page.goto(SERVER_URL);

    const startInput = page.locator('#start_date');
    const endInput = page.locator('#end_date');
    const endDateValue = await endInput.inputValue();
    const sampleDate = endDateValue || (await startInput.inputValue()) || '2024-08-01';

    await startInput.fill(sampleDate);
    await endInput.fill(sampleDate);

    const sampleResponse = {
        success: true,
        stats: {
            total_articles: 2,
            unique_urls: 2,
            dates_with_content: 1,
            dates_processed: 1,
            debug_logs: []
        },
        issues: [
            {
                date: sampleDate,
                source_id: 'test_source',
                category: 'Sample Issue',
                title: 'Sample Issue',
                slug: 'sample-issue',
                url: 'https://example.com/issue',
                newsletter_type: 'daily',
                sections: []
            }
        ],
        articles: [
            {
                date: sampleDate,
                url: 'https://example.com/article-a',
                title: 'Article A (example.com)',
                source_id: 'test_source',
                category: 'Sample Issue',
                section_title: null,
                section_order: null,
                section_emoji: null,
                newsletter_type: 'daily',
                removed: false
            },
            {
                date: sampleDate,
                url: 'https://example.com/article-b',
                title: 'Article B (example.com)',
                source_id: 'test_source',
                category: 'Sample Issue',
                section_title: null,
                section_order: null,
                section_emoji: null,
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

    const scrapeResponse = page.waitForResponse('**/api/scrape');
    await page.getByRole('button', { name: 'Scrape Newsletters' }).click();
    await scrapeResponse;

    const cards = page.locator('.article-card');
    await expect(cards).toHaveCount(2, { timeout: 15000 });

    const firstCard = cards.first();
    const targetUrl = await firstCard.getAttribute('data-url');
    if (!targetUrl) {
        throw new Error('Expected first article to have data-url attribute');
    }

    const targetCard = page.locator(`.article-card[data-url="${targetUrl}"]`);
    const cardHandle = await targetCard.elementHandle();
    if (!cardHandle) {
        throw new Error('Failed to obtain article card element handle');
    }

    const baselineY = await cardHandle.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });

    const removeBtn = targetCard.locator('.remove-article-btn');
    await removeBtn.click();
    await expect(targetCard).toHaveAttribute('data-removed', 'true');
    await page.waitForTimeout(500);

    const removedY = await cardHandle.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    expect(removedY).toBeGreaterThan(baselineY + 20);

    const lastCardUrl = await page.locator('.article-card').last().getAttribute('data-url');
    if (!lastCardUrl) {
        throw new Error('Expected to locate last article after removal');
    }
    expect(lastCardUrl).toBe(targetUrl);

    await removeBtn.click();
    await expect(targetCard).toHaveAttribute('data-removed', 'false');
    await page.waitForTimeout(500);

    const restoredY = await cardHandle.evaluate(el => {
        const rect = el.getBoundingClientRect();
        return rect.top + window.scrollY;
    });
    expect(Math.abs(restoredY - baselineY)).toBeLessThan(15);

    const firstCardUrlAfterRestore = await page.locator('.article-card').first().getAttribute('data-url');
    if (!firstCardUrlAfterRestore) {
        throw new Error('Expected to locate first article after restoration');
    }
    expect(firstCardUrlAfterRestore).toBe(targetUrl);
});
