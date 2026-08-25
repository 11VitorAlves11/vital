import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  framework: "@storybook/react-vite",
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
  // The project ships no telemetry of its own; a build tool does not get to
  // make that promise conditional.
  core: { disableTelemetry: true },
  viteFinal(config) {
    // Storybook inherits vite.config.ts, service worker and all. A catalogue of
    // components has nothing to install and nothing to cache offline, and the
    // worker a preview registers outlives the tab it was opened in. VitePWA
    // contributes a nested array of plugins, so the list is flattened first.
    const isPwa = (plugin: unknown): boolean =>
      !!plugin &&
      typeof plugin === "object" &&
      "name" in plugin &&
      String((plugin as { name: unknown }).name).includes("pwa");
    config.plugins = (config.plugins ?? []).flat(Infinity).filter((plugin) => !isPwa(plugin));
    return config;
  },
};

export default config;
