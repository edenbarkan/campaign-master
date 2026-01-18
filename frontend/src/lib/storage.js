export const safeStorage = {
  get(key, fallback) {
    try {
      const value = window.localStorage.getItem(key);
      return value === null ? fallback : value;
    } catch (err) {
      return fallback;
    }
  },
  set(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (err) {
      // Ignore storage failures (private mode, blocked, etc).
    }
  }
};
