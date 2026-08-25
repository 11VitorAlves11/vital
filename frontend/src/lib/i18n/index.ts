import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "../../locales/en/common.json";
import ptPT from "../../locales/pt-PT/common.json";

export const LANGUAGES = [
  { code: "pt-PT", label: "Português (Portugal)" },
  { code: "en", label: "English" },
] as const;

export const STORAGE_KEY = "vital.language";

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      "pt-PT": { common: ptPT },
      en: { common: en },
    },
    fallbackLng: "en",
    supportedLngs: LANGUAGES.map((language) => language.code),
    defaultNS: "common",
    ns: ["common"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEY,
      caches: ["localStorage"],
    },
  });

/** Keeps <html lang> in step, so assistive technology reads the right language. */
function syncDocumentLanguage(language: string) {
  if (typeof document !== "undefined") document.documentElement.lang = language;
}

syncDocumentLanguage(i18n.resolvedLanguage ?? "pt-PT");
i18n.on("languageChanged", syncDocumentLanguage);

export default i18n;
