// Timezone utilities for automatic local time detection and formatting

/**
 * Gets the browser's timezone
 * @returns The timezone identifier (e.g., 'Asia/Tokyo', 'America/New_York')
 */
export const getBrowserTimezone = (): string => {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
};

/**
 * Converts a UTC timestamp to local time and formats it for Japanese locale
 * @param timestamp ISO timestamp string (assumed to be UTC)
 * @param options Intl.DateTimeFormatOptions for customizing the output
 * @returns Formatted timestamp string in local timezone
 */
export const formatTimestampLocal = (
  timestamp: string,
  options?: Intl.DateTimeFormatOptions
): string => {
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: getBrowserTimezone(),
    ...options
  };

  return new Date(timestamp).toLocaleString('ja-JP', defaultOptions);
};

/**
 * Formats timestamp as relative time in Japanese (e.g., "3分前", "2時間前")
 * Automatically converts UTC to local time for calculation
 * @param timestamp ISO timestamp string (assumed to be UTC)
 * @returns Relative time string in Japanese
 */
export const formatRelativeTimeLocal = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  
  // Calculate difference in milliseconds
  const diffMs = now.getTime() - time.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) {
    return 'たった今';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分前`;
  } else if (diffHours < 24) {
    return `${diffHours}時間前`;
  } else if (diffDays < 7) {
    return `${diffDays}日前`;
  } else {
    // For dates older than 7 days, show the actual date in local time
    return formatTimestampLocal(timestamp, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

/**
 * Formats time only (HH:MM:SS) in local timezone
 * @param timestamp ISO timestamp string (assumed to be UTC)
 * @returns Time string in local timezone (e.g., "14:30:15")
 */
export const formatTimeLocal = (timestamp: string): string => {
  return formatTimestampLocal(timestamp, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

/**
 * Gets current time in local timezone formatted for Japanese locale
 * @returns Current local time string
 */
export const getCurrentTimeLocal = (): string => {
  return new Date().toLocaleTimeString('ja-JP', {
    timeZone: getBrowserTimezone()
  });
};

/**
 * Formats date only in local timezone
 * @param timestamp ISO timestamp string (assumed to be UTC)
 * @returns Date string in local timezone (e.g., "2024/07/23")
 */
export const formatDateLocal = (timestamp: string): string => {
  return formatTimestampLocal(timestamp, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
};

/**
 * Formats timestamp with timezone indicator for Japanese locale
 * @param timestamp ISO timestamp string (assumed to be UTC)
 * @returns Formatted timestamp with timezone (e.g., "2024/07/23 14:30:15 JST")
 */
export const formatTimestampWithTimezone = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: getBrowserTimezone(),
    timeZoneName: 'short'
  });
};

/**
 * Gets the timezone offset in minutes from UTC
 * @returns Timezone offset in minutes (positive for ahead of UTC, negative for behind)
 */
export const getTimezoneOffset = (): number => {
  return -new Date().getTimezoneOffset();
};

/**
 * Gets human-readable timezone name
 * @returns Timezone display name (e.g., "Japan Standard Time")
 */
export const getTimezoneDisplayName = (): string => {
  const options: Intl.DateTimeFormatOptions = {
    timeZoneName: 'long',
    timeZone: getBrowserTimezone()
  };
  
  const parts = new Intl.DateTimeFormat('ja-JP', options).formatToParts(new Date());
  const timeZonePart = parts.find(part => part.type === 'timeZoneName');
  
  return timeZonePart?.value || getBrowserTimezone();
};