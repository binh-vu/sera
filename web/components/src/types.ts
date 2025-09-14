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
export type NavigateFunction = (path: string) => void;
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
  openInNewPage?: boolean;
  children?: React.ReactNode;
}>;