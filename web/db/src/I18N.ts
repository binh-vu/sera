import { MultiLingualString, isMultiLingualString } from "sera-db";

type InterpolationArgs<K extends string | number | symbol = string> = Record<K, MultiLingualString | string>;

/**
 * Represents a translation dictionary structure.
 * 
 * This interface is designed to work similarly to i18next, supporting translations
 * with modifiers such as count and ordinal.
 * 
 * @interface Translation
 * @example
 * // Example structure:
 * {
 *   "en": {
 *     "key_one": "{{ count }} item",
 *     "key_other": "{{ count }} items",
 *   },
 *   "fr": {
 *     "key_one": "élément",
 *     "key_other": "éléments",
 *   }
 * }
 */
interface Translations {
  [lang: string]: {
    [key_and_modifier: string]: string;
  };
}

/**
 * Internationalization (i18n) class for handling translations and localization.
 * 
 * This class holds a string value along with its translations, allowing for runtime language switching.
 * It supports pluralization, ordinalization, and interpolation of variables in the translations.
 * 
 * @class I18N
 */
export class I18NStore {
  /**
   * Singleton instance of the I18NStore.
   * @private
   */
  private static instance: I18NStore;

  /**
   * The current active locale for the application.
   * @private
   */
  private locale: string = 'en';

  /**
   * Store for translation key-value pairs by locale.
   * @private
   */
  private translations: Translations = {};

  /**
   * Creates a new I18N instance.
   * @param initialLocale - The initial locale to use
   * @param initialTranslations - Initial set of translations
   */
  constructor(
    initialLocale?: string,
    initialTranslations?: Translations
  ) {
    if (initialLocale) {
      this.locale = initialLocale;
    }

    if (initialTranslations) {
      this.translations = initialTranslations;
    }
  }

  /**
   * Gets the singleton instance of the I18NStore.
   * If it doesn't exist, it initializes it with default values.
   * @returns The singleton instance of I18NStore
   */
  public static getInstance(): I18NStore {
    if (!I18NStore.instance) {
      I18NStore.instance = new I18NStore();
    }
    return I18NStore.instance;
  }

  /**
   * Gets the current locale.
   * @returns The current locale code
   */
  getLocale(): string {
    return this.locale;
  }

  /**
   * Sets the active locale.
   * @param locale - The locale code to set as active
   */
  setLocale(locale: string): void {
    this.locale = locale;
  }

  /**
   * Registers one or more translations for different languages.
   * 
   * @param translations - An object containing translations mapped by language code.
   *                      The format is { [languageCode: string]: { [key: string]: string } }
   *                      where each language code points to an object of translation keys and values.
   * 
   * @example
   * // Add translations for English and Spanish
   * i18n.registerTranslations({
   *   en: {
   *     greeting: 'Hello',
   *     farewell: 'Goodbye'
   *   },
   *   es: {
   *     greeting: 'Hola',
   *     farewell: 'Adiós'
   *   }
   * });
   */
  registerTranslations(
    translations: Translations
  ): void {

    Object.entries(translations).forEach(([lang, keys]) => {
      if (!this.translations[lang]) {
        this.translations[lang] = {};
      }
      Object.entries(keys).forEach(([key, value]) => {
        this.translations[lang][key] = value;
      });
    });
  }

  /**
   * Translates a key into a localized string with support for pluralization and interpolation.
   * 
   * @param key - The translation key to look up
   * @param options - Configuration options for the translation
   * @param options.locale - Optional locale to use instead of the current locale
   * @param options.count - Optional count for pluralization
   * @param options.ordinal - Whether to use ordinal pluralization rules
   * @param options.args - Optional arguments for string interpolation
   * @returns The translated string or undefined if no translation is found
   * 
   * @example
   * // Basic usage
   * t('greeting'); // => "Hello"
   * 
   * @example
   * // With pluralization
   * t('item', { count: 1 }); // Uses 'item_one'
   * t('item', { count: 5 }); // Uses 'item_other'
   * 
   * @example
   * // With interpolation
   * t('welcome', { args: { name: 'John' } }); // => "Welcome, John!"
   * 
   * @example
   * // With count interpolation
   * t('count', { count: 5 }); // => "Count: 5"
   * 
   * @example
   * // With ordinal pluralization
   * t('position', { count: 1, ordinal: true }); // Uses 'position_ordinal_one'
   */
  public t(key: string, options: { locale?: string, count?: number, ordinal?: boolean, args?: InterpolationArgs } = {}): string | undefined {
    // Handle count-based pluralization and ordinals
    let translationKey = key;
    if (options.count !== undefined) {
      const plural = options.count === 1 ? 'one' : 'other';
      const modifier = options.ordinal ? `ordinal_${plural}` : plural;
      translationKey = `${key}_${modifier}`;
    }

    // Get the translation
    let result = this.translations[options.locale || this.locale]?.[translationKey];
    if (result === undefined) {
      return undefined;
    }

    // Replace any placeholders (string interpolation)
    if (options.count !== undefined) {
      const regex = new RegExp(`{{\\s*count\\s*}}`, 'g');
      result = result.replace(regex, String(options.count));
    }

    if (options.args !== undefined) {
      Object.entries(options.args).forEach(([key, value]) => {
        const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
        let textvalue;
        if (isMultiLingualString(value)) {
          // If the value is a MultiLingualString, get the translation for the current locale
          textvalue = value.lang2value[this.locale] || value.lang2value[value.lang];
        } else {
          textvalue = value;
        }
        result = result.replace(regex, textvalue);
      });
    }

    return result;
  }
}



/**
 * Represents a dynamic multi-lingual string that can be translated into different languages.
 * 
 * This class holds a string value along with its translations, allowing for runtime language switching.
 * It supports pluralization, ordinalization, and interpolation of variables in the translations.
 */
export class DynamicMultiLingualString<K extends string | number | symbol> {
  private key: string;

  constructor(key: string) {
    this.key = key;
  }

  public getLocale(): string {
    return I18NStore.getInstance().getLocale();
  }

  /**
   * Translates a key into a localized string with support for pluralization and interpolation.
   */
  public t(options: { locale?: string, count?: number, ordinal?: boolean, args?: InterpolationArgs<K> } = {}): string {
    const i18n = I18NStore.getInstance();
    const text = i18n.t(this.key, options);
    if (text === undefined) {
      // Fallback to English if translation is not found
      return i18n.t(this.key, { ...options, locale: "en" }) || this.key;
    }
    return text;
  }
}
