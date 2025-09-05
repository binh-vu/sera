import {
} from "@tanstack/react-router";
import React from "react";

export type ReactComponent =
  | React.ComponentClass<any, any>
  | React.FunctionComponent<any>;

export type ArgType = {
  string: string;
  number: number;
  boolean: boolean;
  optionalstring: string | undefined;
  optionalnumber: number | undefined;
  optionalboolean: boolean | undefined;
};

export type ArgSchema<T extends Record<string, keyof ArgType>> = {
  [K in keyof T]: ArgType[T[K]];
};

export type PathDefChildren = Record<
  string,
  PathDef<any, any, PathDefChildren>
>;

export class PathDef<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> {
  // contain the schema of url parameters
  public urlSchema: U;
  // contain the schema of query parameters
  protected querySchema: Q;
  // definition of a path in react-router styles. e.g., /accounts/:id
  public pathDef: string;
  // hold properties of Route component in react-router
  public routeDef: {
    // If this pathDef is a nested route, path can be empty, and if path is empty, it is treated as index route: https://reactrouter.com/start/data/routing#index-routes
    path: string;
    // Whether the path should be matched in a case-sensitive manner
    caseSensitive?: boolean;
    Component: ReactComponent;
  };
  public Component: ReactComponent;
  // Nested routes
  public children: C;

  public constructor({
    urlSchema = {} as U,
    querySchema = {} as Q,
    component: Component,
    pathDef,
    children,
    caseSensitive = false,
  }: {
    urlSchema?: U;
    querySchema?: Q;
    component: ReactComponent;
    pathDef: string;
    children?: C;
    caseSensitive?: boolean;
  }) {
    this.urlSchema = urlSchema;
    this.querySchema = querySchema;
    this.pathDef = pathDef;
    this.children = children || ({} as C);
    this.routeDef = { path: pathDef, caseSensitive, Component };
    this.Component = Component;
  }

  /**
   * Create a path based on the given arguments.
   *
   * Note: this function should be used only when we build a link for <a> element
   * since it won't follow the semantic of react-router but more like when you open a link
   * at the first time in the browser (that's why for hash history, we have to add `#`)
   */
  public getURL({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs: ArgSchema<Q>;
  }): string {
    let path = this.pathDef;

    if (urlArgs !== null) {
      for (let v in urlArgs) {
        path = path.replace(`:${v}`, urlArgs[v] as any as string);
      }
    }

    const query = new URLSearchParams(queryArgs as any).toString();
    if (query.length > 0) {
      path = `${path}?${query}`;
    }

    return path;
  }

  /**
   * Create a location that the history object can be pushed
   */
  public location({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs: ArgSchema<Q>;
  }): RRPath {
    let path = this.pathDef;
    for (let v in urlArgs) {
      path = path.replace(`:${v}`, urlArgs[v] as any as string);
    }

    let query = new URLSearchParams(
      Object.fromEntries(
        Object.entries(queryArgs).filter(([_key, val]) => val !== undefined)
      )
    ).toString();
    query = query.length > 0 ? `?${query}` : query;

    return {
      pathname: path,
      search: query,
      hash: "",
    };
  }

  /**
   * Build a path that can be used to navigate to a link
   */
  public path({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs: ArgSchema<Q>;
  }): Path<U, Q, C> {
    return new Path(this, urlArgs, queryArgs);
  }

  /**
   * Get URL params of this route.
   *
   * @deprecated This function does not work with nested routes. use `useURLParams` or `useParams` hooks instead.
   * @returns null if the route doesn't match or any parameter fails to pass the runtime type check
   */
  public getURLArgs(location: Location<any>): ArgSchema<U> | null {
    const m = matchPath(this.routeDef, location.pathname);
    if (m === null) {
      return null;
    }
    return this.parse(m.params as any, this.urlSchema);
  }

  /**
   * Get query params of this route
   * @returns null if the route doesn't match or any parameter fails to pass the runtime type check
   */
  public getQueryArgs(location: Location<any>): ArgSchema<Q> | null {
    const params = new URLSearchParams(location.search);
    const query = this.parse(
      Object.fromEntries(params.entries()),
      this.querySchema
    );
    if (query !== null && Object.values(query).every((x) => x === undefined)) {
      return null;
    }
    return query;
  }

  /**
   * Parse the object with the schema
   *
   * @param object
   * @param schema
   * @returns
   */
  public parse<T extends Record<string, keyof ArgType>>(
    object: any,
    schema: T
  ): ArgSchema<T> | null {
    const output = {} as any;
    for (const [prop, propType] of Object.entries(schema)) {
      const value = object[prop];
      switch (propType) {
        case "number":
          if (value === undefined) {
            return null;
          }
          output[prop] = parseFloat(value);
          if (!Number.isFinite(output[prop])) {
            return null;
          }
          break;
        case "boolean":
          if (value === undefined || value !== "true" || value !== "false") {
            return null;
          }
          output[prop] = value === "true";
          break;
        case "string":
          if (value === undefined) {
            return null;
          }
          output[prop] = value;
          break;
        case "optionalnumber":
          if (value === undefined) {
            continue;
          }
          output[prop] = parseFloat(value);
          if (!Number.isFinite(output[prop])) {
            return null;
          }
          break;
        case "optionalboolean":
          if (value === undefined) {
            continue;
          }
          if (value !== "true" || value !== "false") {
            return null;
          }
          output[prop] = value === "true";
          break;
        case "optionalstring":
          if (value === undefined) {
            continue;
          }
          output[prop] = value;
          break;
      }
    }
    return output as ArgSchema<T>;
  }
}

/**
 * Overwrite the PathDef class to provide a better using experience
 */
export class NoArgsPathDef<C extends PathDefChildren> extends PathDef<
  {},
  {},
  C
> {
  public getURL(): string {
    return super.getURL({ urlArgs: {}, queryArgs: {} });
  }

  public location(): RRPath {
    return super.location({ urlArgs: {}, queryArgs: {} });
  }

  public path(): Path<{}, {}, C> {
    return super.path({ urlArgs: {}, queryArgs: {} });
  }
}

/**
 * Overwrite the PathDef class to provide a better using experience
 */
export class NoQueryArgsPathDef<
  U extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> extends PathDef<U, {}, C> {
  public getURL({ urlArgs }: { urlArgs: ArgSchema<U> }): string {
    return super.getURL({ urlArgs, queryArgs: {} });
  }

  public location({ urlArgs }: { urlArgs: ArgSchema<U> }): RRPath {
    return super.location({ urlArgs, queryArgs: {} });
  }

  public path({ urlArgs }: { urlArgs: ArgSchema<U> }): Path<U, {}, C> {
    return super.path({ urlArgs, queryArgs: {} });
  }
}

export class NoURLArgsPathDef<
  Q extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> extends PathDef<{}, Q, C> {
  public getURL({ queryArgs }: { queryArgs: ArgSchema<Q> }): string {
    return super.getURL({ urlArgs: {}, queryArgs });
  }

  public location({ queryArgs }: { queryArgs: ArgSchema<Q> }): RRPath {
    return super.location({ urlArgs: {}, queryArgs });
  }

  public path({ queryArgs }: { queryArgs: ArgSchema<Q> }): Path<{}, Q, C> {
    return super.path({ urlArgs: {}, queryArgs });
  }
}

export class OptionalQueryArgsPathDef<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> extends PathDef<U, Q, C> {
  public getURL({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs?: ArgSchema<Q>;
  }): string {
    return super.getURL({
      urlArgs: urlArgs,
      queryArgs: queryArgs || ({} as ArgSchema<Q>),
    });
  }

  public location({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs?: ArgSchema<Q>;
  }): RRPath {
    return super.location({
      urlArgs: urlArgs,
      queryArgs: queryArgs || ({} as ArgSchema<Q>),
    });
  }

  public path({
    urlArgs,
    queryArgs,
  }: {
    urlArgs: ArgSchema<U>;
    queryArgs?: ArgSchema<Q>;
  }): Path<U, Q, C> {
    return super.path({
      urlArgs: urlArgs,
      queryArgs: queryArgs || ({} as ArgSchema<Q>),
    });
  }
}

class Path<
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>,
  C extends PathDefChildren
> {
  private pathDef: PathDef<U, Q, C>;
  private urlArgs: ArgSchema<U>;
  private queryArgs: ArgSchema<Q>;

  public constructor(
    pathDef: PathDef<U, Q, C>,
    urlArgs: ArgSchema<U>,
    queryArgs: ArgSchema<Q>
  ) {
    this.pathDef = pathDef;
    this.urlArgs = urlArgs;
    this.queryArgs = queryArgs;
  }

  /**
   * Open this path
   */
  public open(navigate: NavigateFunction) {
    navigate(
      this.pathDef.location({
        urlArgs: this.urlArgs,
        queryArgs: this.queryArgs,
      })
    );
  }

  public getMouseClickNavigationHandler(navigate: NavigateFunction) {
    return (e?: React.MouseEvent, openInNewPage?: boolean) => {
      this.mouseClickNavigationHandler(navigate, e, openInNewPage);
    };
  }

  /**
   * Handler for a mouse event navigation (e.g., linking on an <a> element)
   */
  public mouseClickNavigationHandler = (
    navigate: NavigateFunction,
    e?: React.MouseEvent,
    openInNewPage?: boolean
  ) => {
    if (e !== undefined) {
      e.preventDefault();
    }

    if (openInNewPage || (e !== undefined && (e.ctrlKey || e.metaKey))) {
      // holding ctrl or cmd key, we should open in new windows
      window.open(
        this.pathDef.getURL({
          urlArgs: this.urlArgs,
          queryArgs: this.queryArgs,
        }),
        "_blank"
      );
      // keep the focus on this page
      window.focus();
    } else {
      navigate(
        this.pathDef.location({
          urlArgs: this.urlArgs,
          queryArgs: this.queryArgs,
        })
      );
    }
  };
}

/**
 * Export routing functions to global navigation behaviour on different platforms
 */
export const routeAPIs = {
  internalHTMLLinkClickFnId: "window._routeAPIs.internalHTMLLinkClick",
  internalHTMLLinkClick:
    (navigate: NavigateFunction) =>
      (e: React.MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();

        let href = (e.target as any).getAttribute("href");
        if (e.ctrlKey || e.metaKey) {
          // holding ctrl or cmd key, we should open in new windows, even in native, because it is internal, another window still work
          window.open(href, "_blank");
          window.focus();
        } else {
          navigate(href);
        }
      },
  goBack: (navigate: NavigateFunction) => navigate(-1),
  goForward: (navigate: NavigateFunction) => navigate(1),
  openInternalLink: (navigate: NavigateFunction, href: string) => {
    navigate(href);
  },
};
(window as any)._routeAPIs = routeAPIs;
