import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useSetPlatformWebsite } from "@/features/platform/hooks";
import type { WebsiteConfigOut } from "@/types/models";

const DEFAULT_THEME_COLOR = "#1c1917";

export function WebsiteConfigPanel({
  businessId,
  businessSlug,
  config,
}: {
  businessId: string;
  businessSlug: string;
  config: WebsiteConfigOut | undefined;
}) {
  const setWebsite = useSetPlatformWebsite(businessId);

  const [isPublished, setIsPublished] = useState(false);
  const [logoUrl, setLogoUrl] = useState("");
  const [heroImageUrl, setHeroImageUrl] = useState("");
  const [story, setStory] = useState("");
  const [themeColor, setThemeColor] = useState(DEFAULT_THEME_COLOR);
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactAddress, setContactAddress] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!config) return;
    setIsPublished(config.is_published);
    setLogoUrl(config.logo_url ?? "");
    setHeroImageUrl(config.hero_image_url ?? "");
    setStory(config.story ?? "");
    setThemeColor(config.theme_color ?? DEFAULT_THEME_COLOR);
    setContactPhone(config.contact_phone ?? "");
    setContactEmail(config.contact_email ?? "");
    setContactAddress(config.contact_address ?? "");
  }, [config]);

  if (!config) return null;

  const previewPath = `/site/${businessSlug}`;

  const handleSave = async () => {
    setError(null);
    try {
      await setWebsite.mutateAsync({
        is_published: isPublished,
        logo_url: logoUrl.trim() || null,
        hero_image_url: heroImageUrl.trim() || null,
        story: story.trim() || null,
        theme_color: themeColor,
        contact_phone: contactPhone.trim() || null,
        contact_email: contactEmail.trim() || null,
        contact_address: contactAddress.trim() || null,
      });
      toast.success("Website saved.");
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between gap-4 border-b border-stone-100 pb-4">
        <div>
          <p className="text-sm font-medium text-stone-800">Published</p>
          <p className="text-xs text-stone-500">
            Live at <span className="font-mono">{businessSlug}.whynotgrace.com</span> once published
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isPublished && (
            <a
              href={previewPath}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline"
            >
              Preview <ExternalLink size={12} />
            </a>
          )}
          <Switch checked={isPublished} onChange={setIsPublished} label="Published" />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="website-logo">Logo image URL</Label>
          <Input id="website-logo" value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} placeholder="https://…" />
        </div>
        <div>
          <Label htmlFor="website-hero">Hero image URL</Label>
          <Input
            id="website-hero"
            value={heroImageUrl}
            onChange={(e) => setHeroImageUrl(e.target.value)}
            placeholder="https://…"
          />
        </div>
      </div>

      <div>
        <Label htmlFor="website-story">Story (optional)</Label>
        <textarea
          id="website-story"
          rows={3}
          value={story}
          onChange={(e) => setStory(e.target.value)}
          placeholder="A line or two about the restaurant — its history, its kitchen, what makes it theirs."
          className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm focus-ring"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <Label htmlFor="website-color">Theme color</Label>
          <div className="flex items-center gap-2">
            <input
              id="website-color"
              type="color"
              value={themeColor}
              onChange={(e) => setThemeColor(e.target.value)}
              className="h-9 w-10 shrink-0 cursor-pointer rounded-md border border-stone-200 p-0.5"
            />
            <Input value={themeColor} onChange={(e) => setThemeColor(e.target.value)} className="font-mono" />
          </div>
        </div>
        <div>
          <Label htmlFor="website-phone">Contact phone</Label>
          <Input id="website-phone" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="website-email">Contact email</Label>
          <Input id="website-email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
        </div>
      </div>

      <div>
        <Label htmlFor="website-address">Address</Label>
        <textarea
          id="website-address"
          rows={2}
          value={contactAddress}
          onChange={(e) => setContactAddress(e.target.value)}
          className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm focus-ring"
        />
      </div>

      <Button size="sm" isLoading={setWebsite.isPending} onClick={() => void handleSave()}>
        Save website
      </Button>
    </div>
  );
}
