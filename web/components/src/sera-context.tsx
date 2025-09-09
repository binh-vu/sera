import { createContext } from "react";
import { ClassName } from "sera-db";

type LinkComponent = React.FunctionComponent<{
  to: any;
  params: { id: string | number };
  openInNewPage?: boolean;
  children: React.ReactNode;
}>;

// EntityRoute should be similar to tanstack router, accepting a parameter id.
export type EntityRoute = { to: any };
export type EntityRoutes = Record<
  ClassName,
  { view: EntityRoute; edit: EntityRoute }
>;

export const SeraContext = createContext<{
  // Link component for navigation, similar to @tanstack/react-router's Link
  link: LinkComponent;
  // Configuration object containing routing information for entities
  entityRoutes: EntityRoutes;
}>({ link: () => null, entityRoutes: {} });

export const SeraContextProvider = ({
  link,
  entityRoutes,
  children,
}: {
  link: LinkComponent;
  entityRoutes: EntityRoutes;
  children: React.ReactNode;
}) => {
  return (
    <SeraContext.Provider value={{ link, entityRoutes }}>
      {children}
    </SeraContext.Provider>
  );
};
