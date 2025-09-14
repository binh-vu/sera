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
> = PathDef<U, Q, C> | { path: PathDef<U, Q, C>;[key: string]: any };

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
 * Check if the route is a grouped route (i.e., it has children)
 *
 * @param route - The route to check
 * @returns True if the route is grouped, false otherwise
 */
function isGroupedRoute<RT extends IRoute<any, any, PathDefChildren>>(
  route: RT | Record<string, RT>
): route is Record<string, RT> {
  return !("path" in route);
}

/**
 * Flatten grouped routes into a single level object with keys as "parent_child"
 *
 * @param routes - The routes object which may contain nested routes
 * @returns A flattened version of the routes object
 */
export function flattenGroupedRoutes<RT extends IRoute<any, any, PathDefChildren>>(
  routes: Record<
    string,
    RT | Record<string, RT>
  >
): Record<string, RT> {
  const flattened: Record<string, RT> = {};

  for (const key in routes) {
    const route = routes[key];
    if (isGroupedRoute(route)) {
      for (const childKey in route) {
        const childRoute = route[childKey];
        flattened[`${key}_${childKey}`] = childRoute;
      }
    } else {
      flattened[key] = route;
    }
  }

  return flattened;
}

/**
 * Update the component of specific routes — typically to apply a layout
 * (for example, to add headers or footers).
 *
 * Note: For some reason, using ReactComponent triggers a TypeScript error
 * highlight in VSCode even though @types/react is available. To work around
 * this, the React component types are duplicated here.
 *
 * @param routes - Route map to update
 * @param applyFn - Either a function applied to every route's component or
 *                  a partial mapping from route keys to such functions.
 *                  Each function receives (component, routeKey, routes)
 *                  and must return a component.
 * @param ignoredRoutes - Optional list, set, or partial route map of routes
 *                        to skip when applying the layout.
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
          component: React.FunctionComponent<any> | React.ComponentClass<any, any>,
          route: keyof R,
          routes: R
        ) => React.FunctionComponent<any> | React.ComponentClass<any, any>
      >
    >
    | ((
      component: React.FunctionComponent<any> | React.ComponentClass<any, any>,
      route: keyof R,
      routes: R
    ) => React.FunctionComponent<any> | React.ComponentClass<any, any>),
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
