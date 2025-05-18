import { useMemo } from "react";
import {
  createBrowserRouter,
  createMemoryRouter,
  RouteObject,
  RouterProvider,
} from "react-router";
import { IRoute, PathDef, ReactComponent } from "./routing";
import { NotFoundComponent } from "./components";
import { PathDefChildren } from "./routing/route";

function toReactRouterRoute(
  route: IRoute<any, any, PathDefChildren>
): RouteObject {
  const pathDef = route instanceof PathDef ? route : route.path;

  if (pathDef.routeDef.path === "") {
    return {
      index: true,
      caseSensitive: pathDef.routeDef.caseSensitive,
      Component: pathDef.routeDef.Component,
    };
  } else {
    return {
      path: pathDef.routeDef.path,
      caseSensitive: pathDef.routeDef.caseSensitive,
      Component: pathDef.routeDef.Component,
      children: Object.values(pathDef.children).map((child) =>
        toReactRouterRoute(child)
      ),
    };
  }
}

export const Router = ({
  routes,
  platform = "web",
  notfound,
}: {
  routes: {
    [name: string]: IRoute<any, any, PathDefChildren>;
  };
  platform?: "native" | "web";
  notfound?: ReactComponent;
}) => {
  const config = useMemo(() => {
    const output = [];
    for (const route of Object.values(routes)) {
      output.push(toReactRouterRoute(route));
    }
    output.push({
      path: "*",
      Component: notfound || NotFoundComponent,
    });
    return output;
  }, [routes]);

  const router =
    platform === "native"
      ? createMemoryRouter(config)
      : createBrowserRouter(config);

  return <RouterProvider router={router} />;
};
