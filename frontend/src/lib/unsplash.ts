/**
 * Product and background image URLs.
 * Uses Picsum Photos (reliable, no API key) - Unsplash Source was deprecated and returns 503.
 */

const PICSUM_BASE = "https://picsum.photos";

export function getProductImage(category: string, id: string): string {
  // Use product id as seed for consistent image per product
  const seed = id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 20) || "product";
  return `${PICSUM_BASE}/seed/${seed}/400/400`;
}

export function getHeroBackground(): string {
  return `${PICSUM_BASE}/seed/hero/1920/1080?blur=2`;
}

export function getCategoryBackground(category: string): string {
  const seed = category.replace(/\s+/g, "").slice(0, 15) || "category";
  return `${PICSUM_BASE}/seed/${seed}/1920/600?blur=2`;
}
