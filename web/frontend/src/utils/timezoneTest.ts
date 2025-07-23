// Test utility to verify timezone functionality
// This file is for development testing only and can be removed after verification

import { 
  getBrowserTimezone, 
  formatTimestampLocal, 
  formatRelativeTimeLocal,
  getCurrentTimeLocal,
  getTimezoneDisplayName 
} from './timezone';

/**
 * Tests timezone functionality and logs results to console
 */
export const testTimezoneFeatures = () => {
  console.group('🌍 Timezone Detection Test');
  
  // Test timezone detection
  const timezone = getBrowserTimezone();
  const displayName = getTimezoneDisplayName();
  console.log(`Browser Timezone: ${timezone}`);
  console.log(`Display Name: ${displayName}`);
  
  // Test current time
  const currentTime = getCurrentTimeLocal();
  console.log(`Current Local Time: ${currentTime}`);
  
  // Test UTC timestamp conversion to local time
  const testTimestamp = '2024-07-23T14:30:15.000Z'; // Sample UTC timestamp
  const localTimestamp = formatTimestampLocal(testTimestamp);
  console.log(`UTC: ${testTimestamp} → Local: ${localTimestamp}`);
  
  // Test relative time formatting
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const relativeTime = formatRelativeTimeLocal(oneHourAgo);
  console.log(`1 hour ago UTC: ${oneHourAgo} → Relative: ${relativeTime}`);
  
  // Test various time differences
  const testTimes = [
    { label: 'Just now', offset: 0 },
    { label: '5 minutes ago', offset: 5 * 60 * 1000 },
    { label: '2 hours ago', offset: 2 * 60 * 60 * 1000 },
    { label: '1 day ago', offset: 24 * 60 * 60 * 1000 },
    { label: '1 week ago', offset: 7 * 24 * 60 * 60 * 1000 }
  ];
  
  console.group('Relative Time Formatting Tests:');
  testTimes.forEach(({ label, offset }) => {
    const testTime = new Date(Date.now() - offset).toISOString();
    const formatted = formatRelativeTimeLocal(testTime);
    console.log(`${label}: ${formatted}`);
  });
  console.groupEnd();
  
  console.groupEnd();
};

/**
 * Tests if Japanese locale formatting is preserved
 */
export const testJapaneseLocale = () => {
  console.group('🇯🇵 Japanese Locale Test');
  
  const testTimestamp = '2024-07-23T14:30:15.000Z';
  const formatted = formatTimestampLocal(testTimestamp);
  
  console.log(`Formatted timestamp: ${formatted}`);
  console.log('Expected format: YYYY/MM/DD HH:MM:SS (Japanese style)');
  
  // Check if format includes Japanese-style date separators
  const hasJapaneseFormat = /\d{4}\/\d{2}\/\d{2}/.test(formatted);
  console.log(`Uses Japanese date format (YYYY/MM/DD): ${hasJapaneseFormat ? '✅' : '❌'}`);
  
  console.groupEnd();
};