import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Phone, Mail, MapPin, ChevronDown } from "lucide-react";

import { Spinner } from "@/components/ui/Spinner";
import { VegIndicator } from "@/components/VegIndicator";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { usePublicWebsite, usePublicWebsiteMenu } from "@/features/website/hooks";

const DEFAULT_ACCENT = "#0284c7";

export function PublicWebsitePage() {
  const { businessSlug } = useParams<{ businessSlug: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: site, isLoading: siteLoading, isError: siteError } = usePublicWebsite(businessSlug);
  const { data: categories } = usePublicWebsiteMenu(businessSlug);
  const [scrolled, setScrolled] = useState(false);

  const kind = searchParams.get("kind");
  const locationId = searchParams.get("location_id");
  const code = searchParams.get("c");
  const orderingUrl =
    businessSlug && kind && locationId && code
      ? `/qr/menu/${businessSlug}/${kind}/${locationId}?c=${encodeURIComponent(code)}`
      : null;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > window.innerHeight * 0.6);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // A scanned table/room QR always lands here first — if this business
  // hasn't got a published website (POS-only, or not set up yet), send the
  // visitor straight into the ordering session it already has a code for,
  // rather than showing them a dead end. See location_service._qr_url.
  useEffect(() => {
    if (siteError && orderingUrl) navigate(orderingUrl, { replace: true });
  }, [siteError, orderingUrl, navigate]);

  if (siteLoading || (siteError && orderingUrl)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <Spinner size={28} className="text-stone-400" />
      </div>
    );
  }

  if (siteError || !site) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-stone-50 px-6 text-center">
        <p className="font-serif text-2xl text-stone-800">{t("website.notFoundTitle")}</p>
        <p className="max-w-sm text-sm text-stone-500">{t("website.notFoundHint")}</p>
      </div>
    );
  }

  const accent = site.config.theme_color || DEFAULT_ACCENT;
  const hasContact = site.config.contact_phone || site.config.contact_email || site.config.contact_address;
  const hasMenu = Boolean(categories && categories.length > 0);

  return (
    <div className="min-h-screen bg-stone-50">
      <header
        className={cn(
          "fixed inset-x-0 top-0 z-50 flex items-center justify-between px-6 py-3 transition-all duration-300",
          scrolled
            ? "translate-y-0 border-b border-stone-200 bg-white/90 opacity-100 backdrop-blur-md"
            : "pointer-events-none -translate-y-full opacity-0"
        )}
      >
        <p className="truncate font-serif text-lg text-stone-900">{site.business_name}</p>
        <div className="flex shrink-0 items-center gap-5">
          {hasMenu && (
            <a href="#menu" className="text-sm font-medium text-stone-600 hover:text-stone-900">
              {t("website.menu")}
            </a>
          )}
          {orderingUrl && (
            <Link
              to={orderingUrl}
              className="rounded-full px-4 py-1.5 text-xs font-semibold text-white shadow-sm"
              style={{ backgroundColor: accent }}
            >
              {t("website.orderNow")}
            </Link>
          )}
        </div>
      </header>

      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-stone-900 px-6 text-center">
        {site.config.hero_image_url && (
          <div
            className="animate-hero-zoom absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${site.config.hero_image_url})` }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-stone-900/30 via-stone-900/45 to-stone-900/85" />

        <div className="animate-fade-in-up relative z-10 flex flex-col items-center">
          {site.config.logo_url ? (
            <img
              src={site.config.logo_url}
              alt={site.business_name}
              className="mb-6 h-16 w-16 rounded-full border border-white/30 object-cover shadow-lg"
            />
          ) : (
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-white/30 bg-white/10 font-serif text-2xl text-white shadow-lg backdrop-blur-sm">
              {site.business_name[0]}
            </div>
          )}
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-white/70">
            {site.business_type.replace(/_/g, " ")}
          </p>
          <h1 className="max-w-3xl text-balance font-serif text-5xl font-medium leading-tight tracking-tight text-white sm:text-6xl">
            {site.business_name}
          </h1>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
            {orderingUrl && (
              <Link
                to={orderingUrl}
                className="rounded-full px-8 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform hover:scale-[1.03]"
                style={{ backgroundColor: accent }}
              >
                {t("website.orderNow")}
              </Link>
            )}
            {hasMenu &&
              (orderingUrl ? (
                <a
                  href="#menu"
                  className="text-sm font-semibold text-white/90 underline underline-offset-4 hover:text-white"
                >
                  {t("website.viewMenu")}
                </a>
              ) : (
                <a
                  href="#menu"
                  className="rounded-full px-8 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform hover:scale-[1.03]"
                  style={{ backgroundColor: accent }}
                >
                  {t("website.viewMenu")}
                </a>
              ))}
          </div>
        </div>

        {hasMenu && (
          <a
            href="#menu"
            aria-hidden="true"
            className="absolute bottom-8 left-1/2 z-10 -translate-x-1/2 animate-bounce text-white/60 hover:text-white/90"
          >
            <ChevronDown size={22} />
          </a>
        )}
      </section>

      {site.config.story && (
        <section className="mx-auto max-w-2xl px-6 py-24 text-center">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.3em]" style={{ color: accent }}>
            {t("website.ourStory")}
          </p>
          <p className="font-serif text-2xl italic leading-relaxed text-stone-700">{site.config.story}</p>
        </section>
      )}

      <section id="menu" className="scroll-mt-16 border-t border-stone-200 px-6 py-24">
        <h2 className="mb-16 text-center font-serif text-3xl text-stone-900">{t("website.menu")}</h2>
        <div className="mx-auto max-w-2xl space-y-14">
          {!hasMenu && <p className="text-center text-sm text-stone-500">{t("website.noMenuYet")}</p>}
          {categories?.map((category) => (
            <div key={category.id}>
              <div className="mb-6 flex items-center gap-4">
                <h3 className="shrink-0 text-sm font-semibold uppercase tracking-[0.2em] text-stone-800">
                  {category.name}
                </h3>
                <div className="h-px flex-1" style={{ backgroundColor: `${accent}33` }} />
              </div>
              <div className="space-y-6">
                {category.items.map((item) => (
                  <div key={item.id}>
                    <div className="flex items-end gap-2">
                      <div className="flex shrink-0 flex-wrap items-center gap-2">
                        <VegIndicator isVeg={item.is_veg} />
                        <p className="font-medium text-stone-900">{item.name}</p>
                        {item.is_specialty && (
                          <span
                            className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                            style={{ borderColor: accent, color: accent }}
                          >
                            {t("website.signature")}
                          </span>
                        )}
                        {item.is_todays_special && (
                          <span
                            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                            style={{ backgroundColor: accent }}
                          >
                            {t("website.todaysSpecial")}
                          </span>
                        )}
                      </div>
                      <div className="mb-1.5 flex-1 border-b border-dotted border-stone-300" />
                      <p className="shrink-0 font-serif text-lg text-stone-800">{formatCurrency(item.price)}</p>
                    </div>
                    {item.description && (
                      <p className="mt-1 max-w-md text-sm leading-relaxed text-stone-500">{item.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-stone-200 bg-stone-100 px-6 py-14 text-center">
        {hasContact && (
          <div className="mx-auto mb-8 flex max-w-lg flex-col items-center gap-2 text-sm text-stone-600">
            <p className="mb-1 text-xs font-semibold uppercase tracking-[0.3em] text-stone-400">
              {t("website.contact")}
            </p>
            {site.config.contact_address && (
              <p className="flex items-center gap-2">
                <MapPin size={14} className="shrink-0 text-stone-400" /> {site.config.contact_address}
              </p>
            )}
            {site.config.contact_phone && (
              <a href={`tel:${site.config.contact_phone}`} className="flex items-center gap-2 hover:text-stone-900">
                <Phone size={14} className="shrink-0 text-stone-400" /> {site.config.contact_phone}
              </a>
            )}
            {site.config.contact_email && (
              <a href={`mailto:${site.config.contact_email}`} className="flex items-center gap-2 hover:text-stone-900">
                <Mail size={14} className="shrink-0 text-stone-400" /> {site.config.contact_email}
              </a>
            )}
          </div>
        )}
        <div className="flex items-center justify-center gap-4">
          <LanguageSwitcher />
        </div>
        <p className="mt-8 text-xs text-stone-400">{t("website.poweredBy")}</p>
      </footer>
    </div>
  );
}
