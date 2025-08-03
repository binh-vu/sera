import { createContext, useContext, useMemo } from "react";
import { IconCheck } from "@tabler/icons-react";
import { MultiLingualString as MLS } from "sera-db";
import { Button, Menu, Text } from "@mantine/core";
import { CountryFlag, CountryFlagComponent, countryFlags } from "./CountryFlag";
import { observer } from "mobx-react-lite";

const chooseLanguage: MLS = {
  lang2value: {
    en: "Choose Language",
    vi: "Chọn ngôn ngữ",
  },
  lang: "en",
};

/**
 * List of supported languages with their names, flags, and locales.
 */
const LANGUAGES: Record<
  string,
  { name: string; flag: CountryFlag; locale: Intl.Locale }
> = {
  en: {
    name: "English",
    flag: countryFlags.US,
    locale: new Intl.Locale("en-US"),
  },
  vi: {
    name: "Tiếng Việt",
    flag: countryFlags.VN,
    locale: new Intl.Locale("vi-VN"),
  },
};

/**
 * A dropdown menu component for selecting application language/locale.
 *
 * Displays the current language with its flag and provides a dropdown menu
 * with all available languages. Each menu item shows the language name,
 * country flag, and a checkmark for the currently selected language.
 *
 * @param locale - The currently selected locale object
 * @param setLocale - Callback function to update the selected locale
 *
 * @example
 * ```tsx
 * <LanguageSelector
 *   locale={currentLocale}
 *   setLocale={setCurrentLocale}
 * />
 * ```
 */
export const LanguageSelector = ({
  locale,
  setLocale,
}: {
  locale: Intl.Locale;
  setLocale: (locale: Intl.Locale) => void;
}) => {
  const menuItems = useMemo(() => {
    return Object.entries(LANGUAGES).map(
      ([languageCode, { flag, name, locale: langLocale }]) => (
        <Menu.Item
          key={languageCode}
          onClick={() => setLocale(langLocale)}
          leftSection={<CountryFlagComponent flag={flag} />}
          rightSection={
            locale.language === languageCode && (
              <IconCheck size={"15"} color="#2986cc" stroke={2} />
            )
          }
        >
          <Text size="sm">{name}</Text>
        </Menu.Item>
      )
    );
  }, [LANGUAGES, locale]);

  return (
    <Menu width={170}>
      <Menu.Target>
        <Button
          variant={"subtle"}
          size={"sm"}
          leftSection={
            <CountryFlagComponent flag={LANGUAGES[locale.language].flag} />
          }
        >
          <Text size="sm">{LANGUAGES[locale.language].name}</Text>
        </Button>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Label>
          <Text size="sm">{chooseLanguage.lang2value[locale.language]}</Text>
        </Menu.Label>
        {menuItems}
      </Menu.Dropdown>
    </Menu>
  );
};

export const LocaleContext = createContext(new Intl.Locale("en-US"));

/**
 * A React context provider component that supplies locale information to its children.
 *
 * This component wraps the LocaleContext.Provider and passes down the locale value
 * from the provided props to all child components that consume the LocaleContext.
 *
 * @param props - The component props
 * @param props.value - An object containing the locale configuration
 * @param props.value.locale - The Intl.Locale instance to be provided to child components
 * @param props.children - React child components that will have access to the locale context
 *
 * @returns A LocaleContext.Provider component wrapping the children
 *
 * @example
 * ```tsx
 * const locale = new Intl.Locale('en-US');
 *
 * <LocaleProvider value={{ locale }}>
 *   <MyComponent />
 * </LocaleProvider>
 * ```
 */
export const LocaleProvider = observer(
  ({
    value,
    children,
  }: {
    value: { locale: Intl.Locale };
    children: React.ReactNode;
  }) => {
    return (
      <LocaleContext.Provider value={value.locale}>
        {children}
      </LocaleContext.Provider>
    );
  }
);

/**
 * A component that returns a multilingual string based on the current locale context.
 *
 * @param props - The component props
 * @param props.value - The multilingual string object containing language-to-value mappings
 * @returns The localized string value for the current locale, or falls back to the default language if the current locale is not available
 *
 * @example
 * ```tsx
 * const multilingualText = {
 *   lang: 'en',
 *   lang2value: {
 *     'en': 'Hello',
 *     'es': 'Hola',
 *     'fr': 'Bonjour'
 *   }
 * };
 *
 * <MultiLingualString value={multilingualText} />
 * ```
 */
export const MultiLingualString = ({ value }: { value: MLS }) => {
  const locale = useContext(LocaleContext);
  return value.lang2value[locale.language] || value.lang2value[value.lang];
};
