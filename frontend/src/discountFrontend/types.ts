export type DiscountType =
  | "new_user"
  | "price_drop"
  | "loyal_customer"
  | "vendor"
  | "festival"
  | "subscription";

export type AppliedDiscount = {
  discount_type: DiscountType;
  label: string;
  description: string;
  percent: number;
  amount: number;
  code?: string;
  product_id?: string;
  valid_until?: string;
};

export type PriceDropNotification = {
  product_id: string;
  product_name: string;
  old_price: number;
  new_price: number;
  percent_off: number;
  image_url?: string;
};

export type SubscriptionTier = {
  id: string;
  name: string;
  discount_percent: number;
  monthly_price: number;
};

export type Festival = {
  id: string;
  label: string;
  percent: number;
  start: string;
  end: string;
};
