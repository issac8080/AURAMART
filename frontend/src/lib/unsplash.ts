/**
 * Product and background image URLs.
 * Prefer product.image_url from API; fallback to Picsum; final fallback is inline SVG (always works).
 */

const PICSUM_BASE = "https://picsum.photos";

/** Placeholder image as data URL - always loads, no network. Use when external image fails. */
export function getProductImagePlaceholder(letter?: string): string {
  const char = (letter || "?").charAt(0).toUpperCase();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect fill="#94a3b8" width="400" height="400"/><text x="50%" y="50%" fill="#1e293b" font-size="120" text-anchor="middle" dy=".35em" font-family="system-ui,sans-serif" font-weight="600">${char}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export function getProductImage(category: string, id: string): string {
  const seed = id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 20) || "product";
  return `${PICSUM_BASE}/seed/${seed}/400/400`;
}

/** Best URL for a product: use API image_url if valid, else generated Picsum URL. */
export function getProductImageSrc(
  imageUrl: string | undefined,
  category: string,
  id: string,
  name?: string
): string {
  if (imageUrl && (imageUrl.startsWith("http://") || imageUrl.startsWith("https://"))) {
    return imageUrl;
  }
  return getProductImage(category, id);
}

export function getHeroBackground(): string {
  return `${PICSUM_BASE}/seed/hero/1920/1080?blur=2`;
}

export function getCategoryBackground(category: string): string {
  const seed = category.replace(/\s+/g, "").slice(0, 15) || "category";
  return `${PICSUM_BASE}/seed/${seed}/1920/600?blur=2`;
}
