import type { ComponentType } from "react";
import {
  LayoutDashboard,
  ShoppingCart,
  Wallet,
  ClipboardList,
  UtensilsCrossed,
  BedDouble,
  ChefHat,
  BookOpen,
  Users,
  Gift,
  Receipt,
  BarChart3,
  UserCog,
  Settings,
  Plug,
  Truck,
  ToggleLeft,
  CreditCard,
} from "lucide-react";
import type { FeatureModule, UserRole } from "@/types/models";

export interface NavItem {
  /** i18n key under nav.* */
  labelKey: string;
  path: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  roles: UserRole[];
  /** Only shown when this feature flag is enabled for the business. */
  featureFlag?: FeatureModule;
}

/**
 * Single source of truth for sidebar navigation. Every `roles` list here
 * is a UI convenience only — it mirrors, but never substitutes for, the
 * backend's actual require_roles() checks (see backend/app/core/permissions.py
 * and each router). Showing fewer items than the backend would technically
 * allow is safe; the reverse is not attempted anywhere here.
 */
export const NAV_ITEMS: NavItem[] = [
  {
    labelKey: "nav.dashboard",
    path: "/",
    icon: LayoutDashboard,
    roles: ["OWNER", "MANAGER"],
  },
  {
    labelKey: "nav.pos",
    path: "/pos",
    icon: ShoppingCart,
    roles: ["OWNER", "MANAGER", "CASH_COUNTER", "SERVICE_COUNTER"],
  },
  {
    labelKey: "nav.orders",
    path: "/orders",
    icon: ClipboardList,
    roles: ["OWNER", "MANAGER", "CASH_COUNTER", "SERVICE_COUNTER"],
  },
  {
    labelKey: "nav.tables",
    path: "/tables",
    icon: UtensilsCrossed,
    roles: ["OWNER", "MANAGER", "SERVICE_COUNTER"],
  },
  {
    labelKey: "nav.rooms",
    path: "/rooms",
    icon: BedDouble,
    roles: ["OWNER", "MANAGER"],
    featureFlag: "HOTEL_ROOMS",
  },
  {
    labelKey: "nav.kitchen",
    path: "/kitchen",
    icon: ChefHat,
    roles: ["OWNER", "MANAGER", "KITCHEN"],
  },
  {
    labelKey: "nav.delivery",
    path: "/delivery",
    icon: Truck,
    roles: ["DELIVERY"],
    featureFlag: "DELIVERY",
  },
  {
    labelKey: "nav.menu",
    path: "/menu",
    icon: BookOpen,
    roles: ["OWNER", "MANAGER"],
  },
  {
    labelKey: "nav.customers",
    path: "/customers",
    icon: Users,
    roles: ["OWNER", "MANAGER", "CASH_COUNTER"],
  },
  {
    labelKey: "nav.loyalty",
    path: "/loyalty",
    icon: Gift,
    roles: ["OWNER", "MANAGER"],
    featureFlag: "LOYALTY",
  },
  {
    labelKey: "nav.shift",
    path: "/shift",
    icon: Wallet,
    // Anyone who handles money needs their own drawer — the person on the
    // counter is the person who counts it.
    roles: ["OWNER", "MANAGER", "CASH_COUNTER"],
  },
  {
    labelKey: "nav.billing",
    path: "/billing",
    icon: Receipt,
    roles: ["OWNER", "MANAGER", "CASH_COUNTER"],
  },
  {
    labelKey: "nav.reports",
    path: "/reports",
    icon: BarChart3,
    roles: ["OWNER", "MANAGER"],
  },
  {
    labelKey: "nav.staff",
    path: "/staff",
    icon: UserCog,
    roles: ["OWNER"],
  },
  {
    labelKey: "nav.integrations",
    path: "/integrations",
    icon: Plug,
    roles: ["OWNER"],
  },
  {
    labelKey: "nav.featureFlags",
    path: "/feature-flags",
    icon: ToggleLeft,
    roles: ["OWNER"],
  },
  {
    labelKey: "nav.settings",
    path: "/settings",
    icon: Settings,
    roles: ["OWNER"],
  },
  {
    labelKey: "nav.subscription",
    path: "/subscription",
    icon: CreditCard,
    roles: ["OWNER"],
  },
];

export function getVisibleNavItems(
  role: UserRole | undefined,
  isFeatureEnabled: (module: FeatureModule) => boolean
): NavItem[] {
  if (!role) return [];
  return NAV_ITEMS.filter((item) => {
    if (!item.roles.includes(role)) return false;
    if (item.featureFlag && !isFeatureEnabled(item.featureFlag)) return false;
    return true;
  });
}
