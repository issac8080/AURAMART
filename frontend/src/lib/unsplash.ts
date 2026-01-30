/**
 * Product and background image URLs.
 * Uses Picsum Photos (reliable, no API key) - Unsplash Source was deprecated and returns 503.
 */

const PICSUM_BASE = "https://picsum.photos";

/** Safe URL for use in CSS url() - encodes & so path is valid */
export function safeImageUrlForCss(url: string | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const u = new URL(url);
    const path = u.pathname.replace(/&/g, "%26");
    return u.origin + path + u.search;
  } catch {
    return undefined;
  }
}

export function getProductImage(category: string, id: string): string {
  // Use product id as seed for consistent image per product
  const seed = id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 20) || "product";
  return `${PICSUM_BASE}/seed/${seed}/400/400`;
}

/** Prefer API image_url, fallback to picsum by category/id */
export function getProductImageUrl(
  imageUrl: string | undefined,
  category: string,
  id: string
): string {
  const safe = safeImageUrlForCss(imageUrl);
  return safe || getProductImage(category, id);
}

export function getHeroBackground(): string {
  return `${PICSUM_BASE}/seed/hero/1920/1080?blur=2`;
}

export function getCategoryBackground(category: string): string {
  const seed = category.replace(/\s+/g, "").slice(0, 15) || "category";
  return `${PICSUM_BASE}/seed/${seed}/1920/600?blur=2`;
}
