import type { ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import { AuthLayout } from "@/layouts/AuthLayout";
import { AppLayout } from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { RoleRoute } from "@/routes/RoleRoute";
import { FeatureRoute } from "@/routes/FeatureRoute";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { ComingSoonPage } from "@/routes/ComingSoonPage";

import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { VerifyEmailPage } from "@/features/auth/VerifyEmailPage";
import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { HomePage } from "@/features/home/HomePage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { PosPage } from "@/features/pos/PosPage";
import { OrdersPage } from "@/features/orders/OrdersPage";
import { KitchenPage } from "@/features/kitchen/KitchenPage";
import { TablesPage } from "@/features/tables/TablesPage";
import { BillingPage } from "@/features/billing/BillingPage";
import { CustomersPage } from "@/features/customers/CustomersPage";
import { MenuAdminPage } from "@/features/menu/MenuAdminPage";
import { RoomsPage } from "@/features/rooms/RoomsPage";
import { StaffPage } from "@/features/staff/StaffPage";
import { FeatureFlagsPage } from "@/features/settings/FeatureFlagsPage";
import { BusinessSettingsPage } from "@/features/settings/BusinessSettingsPage";
import { IntegrationsPage } from "@/features/integrations/IntegrationsPage";
import { LoyaltyPage } from "@/features/loyalty/LoyaltyPage";
import { DeliveryPage } from "@/features/delivery/DeliveryPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { SubscriptionPage } from "@/features/subscription/SubscriptionPage";
import { QrLayout } from "@/features/qr/QrLayout";
import { QrOrderingPage } from "@/features/qr/QrOrderingPage";
import { QrOrderStatusPage } from "@/features/qr/QrOrderStatusPage";

import { NAV_ITEMS } from "@/config/navigation";

// Nav sections with a real page built so far (Phases 3-4). Everything else
// in NAV_ITEMS still falls through to ComingSoonPage below.
const BUILT_PAGES: Record<string, ComponentType> = {
  "/pos": PosPage,
  "/orders": OrdersPage,
  "/kitchen": KitchenPage,
  "/tables": TablesPage,
  "/billing": BillingPage,
  "/customers": CustomersPage,
  "/menu": MenuAdminPage,
  "/rooms": RoomsPage,
  "/staff": StaffPage,
  "/feature-flags": FeatureFlagsPage,
  "/settings": BusinessSettingsPage,
  "/integrations": IntegrationsPage,
  "/loyalty": LoyaltyPage,
  "/delivery": DeliveryPage,
  "/reports": ReportsPage,
  "/subscription": SubscriptionPage,
};

export function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>

        {/* Public, unauthenticated customer QR ordering — never behind
            ProtectedRoute. Access is scoped entirely by the backend's
            per-location QR session (see useQrSessionBootstrap), never by
            a staff login. */}
        <Route element={<QrLayout />}>
          <Route path="/qr/menu/:businessSlug/:kind/:locationId" element={<QrOrderingPage />} />
          <Route path="/qr/menu/:businessSlug/:kind/:locationId/order/:orderId" element={<QrOrderStatusPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/profile" element={<ProfilePage />} />

            {/* Role-gated the same way the sidebar decides visibility —
                see src/config/navigation.ts. Sections without a built page
                yet fall back to ComingSoonPage. */}
            {NAV_ITEMS.filter((item) => item.path !== "/").map((item) => {
              const Page = BUILT_PAGES[item.path];
              const page = Page ? <Page /> : <ComingSoonPage titleKey={item.labelKey} />;
              return (
                <Route key={item.path} element={<RoleRoute allowedRoles={item.roles} />}>
                  {item.featureFlag ? (
                    <Route element={<FeatureRoute module={item.featureFlag} />}>
                      <Route path={item.path} element={page} />
                    </Route>
                  ) : (
                    <Route path={item.path} element={page} />
                  )}
                </Route>
              );
            })}
          </Route>
        </Route>

        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
