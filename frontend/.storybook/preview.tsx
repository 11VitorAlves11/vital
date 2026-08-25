import type { Decorator, Preview } from "@storybook/react-vite";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";

import "../src/design/fonts";
import "../src/index.css";
import { ToastProvider } from "../src/components/ui/Toast";
import i18n from "../src/lib/i18n";

/**
 * Theme and locale are globals rather than per-story args: every story has to be
 * checkable in both themes and both locales, and an argument would have to be
 * declared again on each one.
 *
 * Both effects live in real components — a decorator is a function Storybook
 * renders, but only a component is a place hooks are allowed to run.
 */
function ThemeFrame({ theme, children }: { theme: string; children: ReactNode }) {
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return <div className="min-h-40 bg-surface p-6 text-ink">{children}</div>;
}

function LocaleFrame({ locale, children }: { locale: string; children: ReactNode }) {
  useEffect(() => {
    void i18n.changeLanguage(locale);
  }, [locale]);
  return (
    <I18nextProvider i18n={i18n}>
      {/* Primitives reach for both: Dialog closes with a translated label, and
          anything with a link needs a router above it. */}
      <MemoryRouter>
        <ToastProvider>{children}</ToastProvider>
      </MemoryRouter>
    </I18nextProvider>
  );
}

const withTheme: Decorator = (Story, context) => (
  <ThemeFrame theme={String(context.globals.theme)}>
    <Story />
  </ThemeFrame>
);

const withLocale: Decorator = (Story, context) => (
  <LocaleFrame locale={String(context.globals.locale)}>
    <Story />
  </LocaleFrame>
);

const preview: Preview = {
  decorators: [withTheme, withLocale],
  globalTypes: {
    theme: {
      description: "Theme",
      toolbar: {
        icon: "circlehollow",
        items: [
          { value: "light", title: "Light" },
          { value: "dark", title: "Dark" },
        ],
        dynamicTitle: true,
      },
    },
    locale: {
      description: "Locale",
      toolbar: {
        icon: "globe",
        items: [
          { value: "pt-PT", title: "Português (PT)" },
          { value: "en", title: "English" },
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: "light", locale: "pt-PT" },
  parameters: {
    layout: "fullscreen",
    // The theme decorator paints the surface; Storybook's own backgrounds would
    // sit under it and contradict whichever theme is selected.
    backgrounds: { disable: true },
    controls: { matchers: { color: /(background|color)$/i } },
    a11y: { test: "error" },
  },
};

export default preview;
