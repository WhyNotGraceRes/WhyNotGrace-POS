import { platformApiClient } from "@/api/platformClient";
import type {
  FeatureFlagOut,
  FeatureModule,
  GenericMessageResponse,
  PlatformAccessTokenResponse,
  PlatformBusinessOut,
  PlatformFeatureFlagUpdateRequest,
  PlatformLoginRequest,
  PlatformLogoutRequest,
  PlatformRefreshRequest,
  PlatformToggleUpdateRequest,
  PlatformTokenPairResponse,
  PlatformUserOut,
  ProvisionBusinessRequest,
  ProvisionBusinessResponse,
  ProvisionSubscriptionRequest,
  RenewSubscriptionRequest,
  SetBusinessActiveRequest,
  SubscriptionOut,
  ToggleOut,
} from "@/types/models";

export const platformAuthApi = {
  login: (payload: PlatformLoginRequest) =>
    platformApiClient.post<PlatformTokenPairResponse>("/platform/auth/login", payload).then((r) => r.data),

  refresh: (payload: PlatformRefreshRequest) =>
    platformApiClient.post<PlatformAccessTokenResponse>("/platform/auth/refresh", payload).then((r) => r.data),

  logout: (payload: PlatformLogoutRequest) =>
    platformApiClient.post<GenericMessageResponse>("/platform/auth/logout", payload).then((r) => r.data),

  me: (signal?: AbortSignal) =>
    platformApiClient.get<PlatformUserOut>("/platform/auth/me", { signal }).then((r) => r.data),
};

export const platformBusinessesApi = {
  list: (signal?: AbortSignal) =>
    platformApiClient.get<PlatformBusinessOut[]>("/platform/businesses", { signal }).then((r) => r.data),

  get: (businessId: string, signal?: AbortSignal) =>
    platformApiClient.get<PlatformBusinessOut>(`/platform/businesses/${businessId}`, { signal }).then((r) => r.data),

  provision: (payload: ProvisionBusinessRequest) =>
    platformApiClient.post<ProvisionBusinessResponse>("/platform/businesses", payload).then((r) => r.data),

  setActive: (businessId: string, payload: SetBusinessActiveRequest) =>
    platformApiClient
      .put<PlatformBusinessOut>(`/platform/businesses/${businessId}/active`, payload)
      .then((r) => r.data),
};

export const platformFeaturesApi = {
  list: (businessId: string, signal?: AbortSignal) =>
    platformApiClient
      .get<FeatureFlagOut[]>(`/platform/businesses/${businessId}/features`, { signal })
      .then((r) => r.data),

  set: (businessId: string, module: FeatureModule, payload: PlatformFeatureFlagUpdateRequest) =>
    platformApiClient
      .put<FeatureFlagOut>(`/platform/businesses/${businessId}/features/${module}`, payload)
      .then((r) => r.data),
};

export const platformTogglesApi = {
  list: (businessId: string, signal?: AbortSignal) =>
    platformApiClient.get<ToggleOut[]>(`/platform/businesses/${businessId}/toggles`, { signal }).then((r) => r.data),

  set: (businessId: string, key: string, payload: PlatformToggleUpdateRequest) =>
    platformApiClient
      .put<ToggleOut>(`/platform/businesses/${businessId}/toggles/${key}`, payload)
      .then((r) => r.data),
};

export const platformSubscriptionApi = {
  get: (businessId: string, signal?: AbortSignal) =>
    platformApiClient
      .get<SubscriptionOut>(`/platform/businesses/${businessId}/subscription`, { signal })
      .then((r) => r.data),

  provision: (businessId: string, payload: ProvisionSubscriptionRequest) =>
    platformApiClient
      .post<SubscriptionOut>(`/platform/businesses/${businessId}/subscription/provision`, payload)
      .then((r) => r.data),

  renew: (businessId: string, payload: RenewSubscriptionRequest) =>
    platformApiClient
      .post<SubscriptionOut>(`/platform/businesses/${businessId}/subscription/renew`, payload)
      .then((r) => r.data),

  suspend: (businessId: string) =>
    platformApiClient
      .post<SubscriptionOut>(`/platform/businesses/${businessId}/subscription/suspend`, {})
      .then((r) => r.data),

  cancel: (businessId: string) =>
    platformApiClient
      .post<SubscriptionOut>(`/platform/businesses/${businessId}/subscription/cancel`, {})
      .then((r) => r.data),
};
