import { ClassName } from "sera-db";

export enum Permission {
  /// Allow access to the menu item
  Allow,
  /// Deny access to the menu item
  Denied,
  /// Pending access to the menu item, e.g., waiting for a user role to be set
  Pending
}

/// Typing for Routing
export interface NavigateFunction {
  // same as react-router NavigateFunction
  (to: string | Partial<{
    /**
     * A URL pathname, beginning with a /.
     */
    pathname: string;
    /**
     * A URL search string, beginning with a ?.
     */
    search: string;
    /**
     * A URL fragment identifier, beginning with a #.
     */
    hash: string;
  }>, options?: any): void | Promise<void>;
  (delta: number): void | Promise<void>;
}
// ToDo: improve it should accept dynamic Route Types
export interface NoArgsRoute {
  path(): {
    open: (navigate: NavigateFunction) => void;
  };
  getURL(): string;
}
export interface EntityRoute {
  path({ urlArgs }: { urlArgs: { id: string | number } }): {
    open: (navigate: NavigateFunction) => void;
  };
  getURL({ urlArgs }: { urlArgs: { id: string | number } }): string;
};
export interface EntityRoutes extends Record<
  ClassName,
  { view: EntityRoute; edit: EntityRoute }
> { };
export type LinkComponent = React.FunctionComponent<{
  path: EntityRoute;
  urlArgs: { id: string | number };
  queryArgs: {};
  openInNewPage?: boolean;
  children?: React.ReactNode;
}>;