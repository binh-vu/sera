import {
  matchPath,
  Path as RRPath,
  useLocation,
  useParams as useRRParams,
} from "react-router";
import {
  PathDef,
  ReactComponent,
  ArgType,
  ArgSchema,
  PathDefChildren,
} from "./route";
import { useMemo } from "react";
export { ExternalLink, InternalLink } from "./Link";
export {
  PathDef,
  routeAPIs,
  NoArgsPathDef,
  NoQueryArgsPathDef,
  NoURLArgsPathDef,
  OptionalQueryArgsPathDef,
} from "./route";

export type IRoute<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> = PathDef<U, Q, C> | { path: PathDef<U, Q, C>; [key: string]: any };

/**
 * Find the route that matches with the current location
 */
export function getActiveRouteName(
  location: RRPath,
  routes: { [name: string]: IRoute<any, any, any> }
): string | undefined {
  for (let [name, route] of Object.entries(routes)) {
    const path = route instanceof PathDef ? route : route.path;
    if (matchPath(path.routeDef, location.pathname) !== null) {
      return name;
    }
  }
}

/**
 * Update the component of specific routes -- often for applying layout to the component (add headers/footers)
 *
 * @param routes
 * @param applyFn: mapping from route a function that apply the layout to the component
 * @param ignoredRoutes
 */
export function applyLayout<
  R extends Record<any, IRoute<any, any, PathDefChildren>>
>(
  routes: R,
  applyFn:
    | Partial<
        Record<
          keyof R,
          (
            component: ReactComponent,
            route: keyof R,
            routes: R
          ) => ReactComponent
        >
      >
    | ((
        component: ReactComponent,
        route: keyof R,
        routes: R
      ) => ReactComponent),
  ignoredRoutes?: (keyof R)[] | Set<keyof R> | Partial<R>
) {
  if (ignoredRoutes === undefined) {
    ignoredRoutes = new Set();
  }

  if (Array.isArray(ignoredRoutes)) {
    ignoredRoutes = new Set(ignoredRoutes);
  } else if (!(ignoredRoutes instanceof Set)) {
    ignoredRoutes = new Set(Object.keys(ignoredRoutes));
  }

  if (typeof applyFn === "function") {
    for (let [name, route] of Object.entries(routes)) {
      if (ignoredRoutes.has(name)) continue;
      const path = route instanceof PathDef ? route : route.path;
      path.routeDef.Component = applyFn(path.Component, name, routes);
    }
  } else {
    for (let [name, route] of Object.entries(routes)) {
      if (ignoredRoutes.has(name) || applyFn[name] === undefined) continue;
      const path = route instanceof PathDef ? route : route.path;
      path.routeDef.Component = applyFn[name]!(path.Component, name, routes);
    }
  }
}

/** React hook to get URL parameters */
export function useURLParams<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends { [key: string]: PathDef<any, any, any> }
>(pathDef: PathDef<U, Q, C>): ArgSchema<U> | null {
  const location = useLocation();
  const urlParams = useRRParams();
  return useMemo(() => {
    return pathDef.parse(urlParams, pathDef.urlSchema);
  }, [location.pathname]);
}

/** React hook to get query parameters */
export function useQueryParams<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends { [key: string]: PathDef<any, any, any> }
>(pathDef: PathDef<U, Q, C>): ArgSchema<Q> | null {
  const location = useLocation();
  return useMemo(() => pathDef.getQueryArgs(location), [location.search]);
}

/** React hook to get parameters */
export function useParams<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends { [key: string]: PathDef<any, any, any> }
>(
  pathDef: PathDef<U, Q, C>
): { url: ArgSchema<U> | null; query: ArgSchema<Q> | null } {
  return { url: useURLParams(pathDef), query: useQueryParams(pathDef) };
}

export type { ReactComponent, ArgType, ArgSchema };
