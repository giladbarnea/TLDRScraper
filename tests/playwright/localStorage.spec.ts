import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import process from 'process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const SERVER_PORT = '5002';
const SERVER_URL = `http://127.0.0.1:${SERVER_PORT}/`;
const SAMPLE_DATE = '2024-08-01';

const SAMPLE_SCRAPE_RESPONSE = {
    success: true,
    stats: {
        total_articles: 1,
        unique_urls: 1,
        dates_with_content: 1,
        dates_processed: 1,
        debug_logs: []
    },
    issues: [
        {
            date: SAMPLE_DATE,
            source_id: 'test_source',
            category: 'AI',
            title: 'AI Highlights',
            slug: 'ai-highlights',
            url: 'https://example.com/issues/ai',
            newsletter_type: 'daily',
            sections: []
        }
    ],
    articles: [
        {
            date: SAMPLE_DATE,
            url: 'https://example.com/articles/a',
            title: 'Example AI Article',
            source_id: 'test_source',
            category: 'AI',
            section_title: null,
            section_order: null,
            section_emoji: null,
            newsletter_type: 'daily',
            removed: false
        }
    ]
};

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
            // retry
        }
        await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw new Error('Timed out waiting for server to start');
}

test.beforeAll(async () => {
    serverProcess = spawn(
        'uv',
        ['run', 'flask', '--app', 'serve', 'run', '--port', SERVER_PORT, '--no-reload'],
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

async function navigateToApp(page: Page) {
    await test.step('Navigate to TLDR scraper UI', async () => {
        await page.goto(SERVER_URL);
        await page.waitForSelector('#scrapeBtn', { state: 'visible' });
    });
}

async function ensureEmptyLocalStorage(page: Page) {
    await test.step('Verify localStorage is empty before actions', async () => {
        const keys = await page.evaluate(() => Object.keys(window.localStorage));
        console.log('[localStorage] keys before test action', keys);
        expect(keys).toEqual([]);
    });
}

async function triggerMockScrape(page: Page) {
    await test.step('Mock the scrape API response', async () => {
        await page.route('**/api/scrape', route => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(SAMPLE_SCRAPE_RESPONSE)
            });
        });
    });

    await test.step('Submit the scrape form for a single day', async () => {
        const startInput = page.locator('#start_date');
        const endInput = page.locator('#end_date');
        await startInput.fill(SAMPLE_DATE);
        await endInput.fill(SAMPLE_DATE);

        const scrapeResponse = page.waitForResponse('**/api/scrape');
        await page.getByRole('button', { name: 'Scrape Newsletters' }).click();
        await scrapeResponse;
        console.log('[scrape] triggered for', SAMPLE_DATE);
    });
}

test.describe('localStorage persistence flows', () => {
    test.beforeEach(async ({ page }) => {
        await navigateToApp(page);
        await page.evaluate(() => window.localStorage.clear());
    });

    test('localStorage starts empty on initial page load', async ({ page }) => {
        await ensureEmptyLocalStorage(page);
    });

    test('scrape results are cached to localStorage', async ({ page }) => {
        await ensureEmptyLocalStorage(page);
        await triggerMockScrape(page);

        await test.step('Validate cached payload for the requested date', async () => {
            const storageKey = `newsletters:scrapes:${SAMPLE_DATE}`;
            const stored = await page.evaluate(key => window.localStorage.getItem(key), storageKey);
            expect(stored, 'Expected scrape payload to be stored in localStorage').not.toBeNull();
            const payload = JSON.parse(stored!);
            console.log('[localStorage] stored payload keys', Object.keys(payload));
            expect(payload.date).toBe(SAMPLE_DATE);
            expect(Array.isArray(payload.articles) ? payload.articles.length : 0).toBe(1);
            expect(payload.articles[0].url).toBe('https://example.com/articles/a');
        });
    });
});
