// Cache utility for storing resume analysis data
const CACHE_KEY_PREFIX = 'resume_analysis_';
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes in milliseconds

interface CacheItem {
  data: any;
  timestamp: number;
  version: string;
}

// Generate a cache key for a specific resume
const getCacheKey = (resumeId: string, dataType: string): string => {
  return `${CACHE_KEY_PREFIX}${resumeId}_${dataType}`;
};

// Store data in cache
export const setCache = (resumeId: string, dataType: string, data: any): void => {
  try {
    const cacheKey = getCacheKey(resumeId, dataType);
    const cacheItem: CacheItem = {
      data,
      timestamp: Date.now(),
      version: '1.0' // Increment this when data structure changes
    };
    
    // Store in localStorage
    localStorage.setItem(cacheKey, JSON.stringify(cacheItem));
  } catch (error) {
    console.warn('Failed to set cache:', error);
  }
};

// Retrieve data from cache
export const getCache = (resumeId: string, dataType: string): any => {
  try {
    const cacheKey = getCacheKey(resumeId, dataType);
    const cachedItemStr = localStorage.getItem(cacheKey);
    
    if (!cachedItemStr) {
      return null;
    }
    
    const cachedItem: CacheItem = JSON.parse(cachedItemStr);
    
    // Check if cache is expired
    if (Date.now() - cachedItem.timestamp > CACHE_DURATION) {
      // Remove expired cache
      localStorage.removeItem(cacheKey);
      return null;
    }
    
    // Check version compatibility
    if (cachedItem.version !== '1.0') {
      // Remove outdated cache
      localStorage.removeItem(cacheKey);
      return null;
    }
    
    return cachedItem.data;
  } catch (error) {
    console.warn('Failed to get cache:', error);
    return null;
  }
};

// Clear cache for a specific resume
export const clearCache = (resumeId: string): void => {
  try {
    const keysToRemove: string[] = [];
    
    // Find all cache keys for this resume
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(`${CACHE_KEY_PREFIX}${resumeId}_`)) {
        keysToRemove.push(key);
      }
    }
    
    // Remove all keys
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (error) {
    console.warn('Failed to clear cache:', error);
  }
};

// Clear all resume analysis cache
export const clearAllCache = (): void => {
  try {
    const keysToRemove: string[] = [];
    
    // Find all resume analysis cache keys
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_KEY_PREFIX)) {
        keysToRemove.push(key);
      }
    }
    
    // Remove all keys
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (error) {
    console.warn('Failed to clear all cache:', error);
  }
};

// Get cache stats
export const getCacheStats = (): { count: number; size: number } => {
  try {
    let count = 0;
    let size = 0;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_KEY_PREFIX)) {
        count++;
        const item = localStorage.getItem(key);
        if (item) {
          size += item.length;
        }
      }
    }
    
    return { count, size };
  } catch (error) {
    console.warn('Failed to get cache stats:', error);
    return { count: 0, size: 0 };
  }
};