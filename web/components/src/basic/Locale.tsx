import { observer } from "mobx-react-lite";
import { createContext } from "react";

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
