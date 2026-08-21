import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
// Utility function to merge class names with Tailwind
export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

// ─── Number Formatting (English locale: comma=thousands, dot=decimal) ────────
const enFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const enFormatter1 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const enFormatterInt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/**
 * Format a number with English locale (comma as thousands separator, dot as decimal).
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 2)
 */
export function formatNumber(value, decimals = 2) {
    if (value == null || isNaN(value)) return "N/A";
    if (decimals === 0) return enFormatterInt.format(value);
    if (decimals === 1) return enFormatter1.format(value);
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    }).format(value);
}

/**
 * Format an integer with thousands separators (English locale).
 */
export function formatInt(value) {
    if (value == null || isNaN(value)) return "N/A";
    return enFormatterInt.format(value);
}

// Utility function to format a number with currency
export function formatCurrency(amount, currency = "USD", options) {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        ...options,
    }).format(amount);
}
// Utility function to generate a unique ID
export function generateUniqueId(prefix = "id") {
    return `${prefix}-${Math.random().toString(36).substring(2, 9)}`;
}
// Utility function to truncate text
export function truncateText(text, maxLength) {
    if (text.length <= maxLength)
        return text;
    return text.substring(0, maxLength) + "...";
}
// Utility function to format date
export function formatDate(date, options) {
    return new Intl.DateTimeFormat("en-US", {
        day: "numeric",
        month: "short",
        year: "numeric",
        ...options,
    }).format(date);
}
// Utility function to debounce function calls
export function debounce(func, wait) {
    let timeout = null;
    return function (...args) {
        const later = () => {
            timeout = null;
            func(...args);
        };
        if (timeout !== null) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(later, wait);
    };
}
// Utility function to throttle function calls
export function throttle(func, limit) {
    let inThrottle = false;
    return function (...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => {
                inThrottle = false;
            }, limit);
        }
    };
}
