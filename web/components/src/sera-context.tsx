import { createContext } from "react";
import { EntityRoutes, LinkComponent } from "./types";

export const SeraContext = createContext<{
  // Link component for navigation, similar to sera-route InternalLink
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
