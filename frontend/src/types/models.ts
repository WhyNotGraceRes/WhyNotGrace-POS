/**
 * Ergonomic aliases for the auto-generated OpenAPI schema types in
 * ./api.ts (see package.json "codegen" script — regenerate after any
 * backend schema change, never hand-edit api.ts, never invent shapes
 * here that don't exist in the backend schema).
 */
import type { components } from "./api";

export type Schemas = components["schemas"];

// --- Auth ---
export type RegisterRequest = Schemas["RegisterRequest"];
export type RegisterResponse = Schemas["RegisterResponse"];
export type LoginRequest = Schemas["LoginRequest"];
export type TokenPairResponse = Schemas["TokenPairResponse"];
export type AccessTokenResponse = Schemas["AccessTokenResponse"];
export type RefreshRequest = Schemas["RefreshRequest"];
export type LogoutRequest = Schemas["LogoutRequest"];
export type ForgotPasswordRequest = Schemas["ForgotPasswordRequest"];
export type ResetPasswordRequest = Schemas["ResetPasswordRequest"];
export type VerifyEmailRequest = Schemas["VerifyEmailRequest"];
export type ResendVerificationRequest = Schemas["ResendVerificationRequest"];
export type GenericMessageResponse = Schemas["GenericMessageResponse"];
export type UserOut = Schemas["UserOut"];

// --- Enums ---
export type BusinessType = Schemas["BusinessType"];
export type UserRole = Schemas["UserRole"];
export type FeatureModule = Schemas["FeatureModule"];

// --- Business / settings ---
export type BusinessOut = Schemas["BusinessOut"];
export type BusinessUpdateRequest = Schemas["BusinessUpdateRequest"];
export type BusinessSettingsOut = Schemas["BusinessSettingsOut"];
export type BusinessSettingsUpdateRequest = Schemas["BusinessSettingsUpdateRequest"];

// --- Feature flags ---
export type FeatureFlagOut = Schemas["FeatureFlagOut"];
export type FeatureFlagUpdateRequest = Schemas["FeatureFlagUpdateRequest"];

// --- Dashboard ---
export type DashboardResponse = Schemas["DashboardResponse"];
export type TopMenuItemOut = Schemas["TopMenuItemOut"];

// --- Menu ---
export type MenuVariantOut = Schemas["MenuVariantOut"];
export type MenuOptionOut = Schemas["MenuOptionOut"];
export type MenuCategoryOut = Schemas["MenuCategoryOut"];

/** Pydantic serializes `variants`/`option_groups`/`options` as `[]` when
 * unset (Field(default_factory=list)) — always present at runtime — but
 * since they carry a default they're absent from the OpenAPI `required`
 * list, so openapi-typescript marks them optional. api/normalize.ts
 * guarantees the array is always present; these aliases describe that
 * post-normalization shape so callers don't need `?? []` everywhere. */
export type MenuOptionGroupOut = Omit<Schemas["MenuOptionGroupOut"], "options"> & {
  options: MenuOptionOut[];
};
export type MenuItemOut = Omit<Schemas["MenuItemOut"], "variants" | "option_groups"> & {
  variants: MenuVariantOut[];
  option_groups: MenuOptionGroupOut[];
};

// --- Menu admin (create/update) ---
/** See GenerateBillRequest above — scalar-default-marked-required quirk. */
export type MenuCategoryCreate = Omit<Schemas["MenuCategoryCreate"], "display_order"> & { display_order?: number };
export type MenuCategoryUpdate = Schemas["MenuCategoryUpdate"];

export type MenuVariantCreate = Omit<Schemas["MenuVariantCreate"], "price_delta" | "is_default"> & {
  price_delta?: number;
  is_default?: boolean;
};
export type MenuOptionCreate = Omit<Schemas["MenuOptionCreate"], "price_delta" | "display_order"> & {
  price_delta?: number;
  display_order?: number;
};
export type MenuOptionGroupCreate = Omit<
  Schemas["MenuOptionGroupCreate"],
  "is_required" | "allow_multiple" | "display_order" | "options"
> & {
  is_required?: boolean;
  allow_multiple?: boolean;
  display_order?: number;
  options?: MenuOptionCreate[];
};
export type MenuItemCreate = Omit<
  Schemas["MenuItemCreate"],
  "is_veg" | "display_order" | "variants" | "option_groups"
> & {
  is_veg?: boolean;
  display_order?: number;
  variants?: MenuVariantCreate[];
  option_groups?: MenuOptionGroupCreate[];
};
export type MenuItemUpdate = Schemas["MenuItemUpdate"];

export type MenuVariantUpdate = Schemas["MenuVariantUpdate"];
export type MenuOptionGroupUpdate = Schemas["MenuOptionGroupUpdate"];
export type MenuOptionUpdate = Schemas["MenuOptionUpdate"];

// --- Pricing contexts ---
export type PriceRuleOut = Schemas["PriceRuleOut"];
export type PriceRuleCreate = Schemas["PriceRuleCreate"];
export type PriceRuleUpdate = Schemas["PriceRuleUpdate"];

// --- Locations / tables / rooms ---
export type LocationOut = Schemas["LocationOut"];
export type LocationType = Schemas["LocationType"];
export type LocationStatus = Schemas["LocationStatus"];
export type LocationCreate = Schemas["LocationCreate"];
export type LocationUpdate = Schemas["LocationUpdate"];

// --- Orders ---
export type OrderCreateRequest = Schemas["OrderCreateRequest"];
export type OrderItemCreate = Schemas["OrderItemCreate"];
export type OrderItemOptionOut = Schemas["OrderItemOptionOut"];
export type OrderSource = Schemas["OrderSource"];
export type OrderStatus = Schemas["OrderStatus"];
export type PricingContext = Schemas["PricingContext"];

/** See MenuItemOut above — same default-array optionality quirk. */
export type OrderItemOut = Omit<Schemas["OrderItemOut"], "options"> & {
  options: OrderItemOptionOut[];
};
export type OrderCustomerBriefOut = Schemas["OrderCustomerBriefOut"];
export type DeliveryStatus = Schemas["DeliveryStatus"];

export type OrderOut = Omit<Schemas["OrderOut"], "items"> & {
  items: OrderItemOut[];
};

// --- KOT ---
export type KOTItemOut = Schemas["KOTItemOut"];
export type KOTStatusUpdateRequest = Schemas["KOTStatusUpdateRequest"];
export type KOTStatus = Schemas["KOTStatus"];

/** See MenuItemOut above — same default-array optionality quirk. */
export type KOTOut = Omit<Schemas["KOTOut"], "items"> & {
  items: KOTItemOut[];
};

// --- Billing ---
export type BillItemOut = Schemas["BillItemOut"];
export type BillLineOut = Schemas["BillLineOut"];
export type BillStatus = Schemas["BillStatus"];
export type BillTaxCreate = Schemas["BillTaxCreate"];
export type BillServiceChargeCreate = Schemas["BillServiceChargeCreate"];
export type ApplyDiscountRequest = Schemas["ApplyDiscountRequest"];

/** openapi-typescript renders Pydantic fields that carry a `default=` as
 * required-with-a-value rather than optional, because the JSON Schema
 * shows a concrete default — but a field with a default is, by
 * definition, never required in the actual request body. Callers
 * shouldn't have to pass `use_default_tax`/`use_default_service_charge`
 * just to satisfy the type when they're happy with the (real) backend
 * default of `true`. */
export type GenerateBillRequest = Omit<Schemas["GenerateBillRequest"], "use_default_tax" | "use_default_service_charge"> & {
  use_default_tax?: boolean;
  use_default_service_charge?: boolean;
};

/** See MenuItemOut above — same default-array optionality quirk. */
export type BillOut = Omit<Schemas["BillOut"], "items" | "taxes" | "discounts" | "service_charges"> & {
  items: BillItemOut[];
  taxes: BillLineOut[];
  discounts: BillLineOut[];
  service_charges: BillLineOut[];
};

// --- Payments ---
export type PaymentMethod = Schemas["PaymentMethod"];
export type PaymentStatus = Schemas["PaymentStatus"];
export type PaymentOut = Schemas["PaymentOut"];
export type CashPaymentRequest = Schemas["CashPaymentRequest"];
export type RazorpayOrderCreateRequest = Schemas["RazorpayOrderCreateRequest"];
export type RazorpayOrderCreateResponse = Schemas["RazorpayOrderCreateResponse"];
export type RazorpayVerifyRequest = Schemas["RazorpayVerifyRequest"];

// --- Customers ---
export type CustomerOut = Schemas["CustomerOut"];
export type CustomerUpdate = Schemas["CustomerUpdate"];

/** See GenerateBillRequest above — same default-value-marked-required quirk. */
export type CustomerCreate = Omit<
  Schemas["CustomerCreate"],
  "marketing_opt_in" | "sms_opt_in" | "email_opt_in" | "whatsapp_opt_in"
> & {
  marketing_opt_in?: boolean;
  sms_opt_in?: boolean;
  email_opt_in?: boolean;
  whatsapp_opt_in?: boolean;
};

// --- Loyalty ---
export type LoyaltyAccountOut = Schemas["LoyaltyAccountOut"];
export type RewardOut = Schemas["RewardOut"];
export type LoyaltyRuleOut = Schemas["LoyaltyRuleOut"];
export type LoyaltyRuleCreate = Schemas["LoyaltyRuleCreate"];
export type LoyaltyRuleUpdate = Schemas["LoyaltyRuleUpdate"];
export type RedeemRewardRequest = Schemas["RedeemRewardRequest"];

// --- Staff ---
export type StaffOut = Schemas["StaffOut"];
export type StaffCreateRequest = Schemas["StaffCreateRequest"];
export type StaffUpdateRequest = Schemas["StaffUpdateRequest"];

// --- Integrations ---
export type IntegrationOut = Schemas["IntegrationOut"];
export type IntegrationProvider = Schemas["IntegrationProvider"];
export type ConnectCredentialsRequest = Schemas["ConnectCredentialsRequest"];

// --- Delivery (staff-facing status updates) ---
export type DeliveryStatusUpdateRequest = Schemas["DeliveryStatusUpdateRequest"];

// --- Subscription (₹699/month platform billing — see backend/app/api/subscription.py) ---
export type SubscriptionOut = Schemas["SubscriptionOut"];
export type SubscriptionCheckoutResponse = Schemas["SubscriptionCheckoutResponse"];
export type SubscriptionVerifyRequest = Schemas["SubscriptionVerifyRequest"];

// --- Audit log ---
export type AuditLogOut = Schemas["AuditLogOut"];

/** backend/app/api/reports.py declares no `response_model` (the router
 * returns the raw dicts built by app/services/reports_service.py), so
 * openapi-typescript can't generate these shapes — they are hand-written
 * here to match reports_service.py exactly, not invented independently. */
export interface SalesReportRow {
  period: string;
  total_sales: number;
  bills_paid: number;
}
export interface OrderCountReportRow {
  source: OrderSource;
  order_count: number;
}
export interface PaymentBreakdownReportRow {
  method: PaymentMethod;
  count: number;
  total_amount: number;
}
export interface TopItemReportRow {
  menu_item_id: string;
  name: string;
  quantity_sold: number;
  revenue: number;
}
export interface CategoryPerformanceReportRow {
  category_id: string;
  category_name: string;
  revenue: number;
}
export interface ChannelPerformanceReportRow {
  channel: OrderSource;
  order_count: number;
  revenue: number;
}
export interface ReportDateRangeParams {
  start_date?: string;
  end_date?: string;
}

// --- QR ordering (public, unauthenticated) ---
export type QRScanResponse = Schemas["QRScanResponse"];
export type QRMenuOptionOut = Schemas["QRMenuOptionOut"];
export type QRMenuOptionGroupOut = Schemas["QRMenuOptionGroupOut"];
export type QRMenuVariantOut = Schemas["QRMenuVariantOut"];
export type QRMenuItemOut = Schemas["QRMenuItemOut"];
export type QRMenuCategoryOut = Schemas["QRMenuCategoryOut"];
export type QRMenuResponse = Schemas["QRMenuResponse"];
export type QRCartItem = Schemas["QRCartItem"];
export type QROrderCreateRequest = Schemas["QROrderCreateRequest"];

// --- Validation errors (FastAPI 422 shape) ---
export type ValidationError = Schemas["ValidationError"];
export type HTTPValidationError = Schemas["HTTPValidationError"];
