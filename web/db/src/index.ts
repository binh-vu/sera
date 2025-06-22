export * from "./Table";
export * from "./DB";
export * from "./Query";
export * from "./Record";
export * from "./TableIndex";
export * from "./Schema";
export * as validators from "./validators";
export * as normalizers from "./normalizers";
export { DynamicMultiLingualString, I18NStore } from "./I18N";

/**
 * Register a default error handler for all ajax requests via axios, which simply show a bubble message, and re-throw the error.
 *
 * The implementation leverages the feature that when a Promise that has no rejection handler is rejected, the unhandledrejection event is sent to the global scope.
 *
 * More information and browser supports can be found in here: https://developer.mozilla.org/en-US/docs/Web/API/Window/unhandledrejection_event
 *
 * In Mar 2022, most of the important browsers support this feature except IE and Firefox for Android.
 */
export const registerDefaultAxiosErrorHandler = (
  fn: (event: PromiseRejectionEvent) => void
) => {
  window.addEventListener("unhandledrejection", (event) => {
    if (event.reason.isAxiosError === true) {
      fn(event);
      console.error(event.reason);
    }
  });
};
