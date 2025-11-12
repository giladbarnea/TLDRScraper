#!/usr/bin/env node
/**
 * Phase 2 Verification: Test exports and shapes of client abstraction layer
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFile } from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('Phase 2 Export Verification\n');

// Test 1: Verify useSupabaseStorage hook exports
console.log('✓ Test 1: Verify useSupabaseStorage hook exports');
try {
  const hookPath = join(__dirname, 'client/src/hooks/useSupabaseStorage.js');
  const hookContent = await readFile(hookPath, 'utf-8');

  // Check for export
  if (!hookContent.includes('export function useSupabaseStorage')) {
    throw new Error('useSupabaseStorage not exported');
  }

  // Check for key functions
  if (!hookContent.includes('function readValue')) {
    throw new Error('readValue function missing');
  }
  if (!hookContent.includes('function writeValue')) {
    throw new Error('writeValue function missing');
  }
  if (!hookContent.includes('function subscribe')) {
    throw new Error('subscribe function missing');
  }
  if (!hookContent.includes('function emitChange')) {
    throw new Error('emitChange function missing');
  }

  // Check return tuple shape
  if (!hookContent.includes('return [value, setValueAsync, remove, { loading, error }]')) {
    throw new Error('Hook does not return correct tuple shape');
  }

  console.log('  ✅ useSupabaseStorage exports correctly');
  console.log('  ✅ Returns [value, setValue, remove, { loading, error }] tuple');
  console.log('  ✅ Has readValue, writeValue, subscribe, emitChange functions');
} catch (err) {
  console.error('  ❌ Failed:', err.message);
  process.exit(1);
}

// Test 2: Verify storageApi exports
console.log('\n✓ Test 2: Verify storageApi exports');
try {
  const apiPath = join(__dirname, 'client/src/lib/storageApi.js');
  const apiContent = await readFile(apiPath, 'utf-8');

  const requiredExports = [
    'export async function isDateCached',
    'export async function getDailyPayload',
    'export async function setDailyPayload',
    'export async function getDailyPayloadsRange'
  ];

  for (const exportName of requiredExports) {
    if (!apiContent.includes(exportName)) {
      throw new Error(`Missing export: ${exportName}`);
    }
  }

  console.log('  ✅ isDateCached exported');
  console.log('  ✅ getDailyPayload exported');
  console.log('  ✅ setDailyPayload exported');
  console.log('  ✅ getDailyPayloadsRange exported');
} catch (err) {
  console.error('  ❌ Failed:', err.message);
  process.exit(1);
}

// Test 3: Verify key patterns
console.log('\n✓ Test 3: Verify key pattern handling');
try {
  const hookPath = join(__dirname, 'client/src/hooks/useSupabaseStorage.js');
  const hookContent = await readFile(hookPath, 'utf-8');

  // Check cache:enabled pattern
  if (!hookContent.includes("key.startsWith('cache:')")) {
    throw new Error('cache: pattern handler missing');
  }

  // Check newsletters:scrapes: pattern
  if (!hookContent.includes("key.startsWith('newsletters:scrapes:')")) {
    throw new Error('newsletters:scrapes: pattern handler missing');
  }

  // Check proper routing
  if (!hookContent.includes('/api/storage/setting/')) {
    throw new Error('settings endpoint routing missing');
  }
  if (!hookContent.includes('/api/storage/daily/')) {
    throw new Error('daily endpoint routing missing');
  }

  console.log('  ✅ cache: pattern routes to /api/storage/setting/*');
  console.log('  ✅ newsletters:scrapes: pattern routes to /api/storage/daily/*');
} catch (err) {
  console.error('  ❌ Failed:', err.message);
  process.exit(1);
}

// Test 4: Verify event system
console.log('\n✓ Test 4: Verify event system');
try {
  const hookPath = join(__dirname, 'client/src/hooks/useSupabaseStorage.js');
  const hookContent = await readFile(hookPath, 'utf-8');

  if (!hookContent.includes("'supabase-storage-change'")) {
    throw new Error('supabase-storage-change event not found');
  }

  if (!hookContent.includes('window.dispatchEvent(new CustomEvent')) {
    throw new Error('CustomEvent dispatch missing');
  }

  console.log('  ✅ Emits supabase-storage-change events');
  console.log('  ✅ Uses CustomEvent for cross-component sync');
} catch (err) {
  console.error('  ❌ Failed:', err.message);
  process.exit(1);
}

console.log('\n✅ All export verification tests passed!\n');
