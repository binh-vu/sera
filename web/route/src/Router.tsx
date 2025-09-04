import { useMemo } from "react";
import { IRoute, PathDef, ReactComponent } from "./routing";
import { NotFoundComponent } from "./components";
import { PathDefChildren } from "./routing/route";
import {
  Outlet,
  RouterProvider,
  Link,
  createRouter,
  createRoute,
  createRootRoute,
  Route,
} from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

function toTanStackRoute(
  route: IRoute<any, any, PathDefChildren>,
  parentRoute?: Route<any, any>
): Route<any, any> {
  const pathDef = route instanceof PathDef ? route : route.path;

  if (pathDef.routeDef.path === "") {
    return createRootRoute({
      component: pathDef.routeDef.Component as any,
    });
  } else {
    if (parentRoute === undefined) {
      throw new Error(
        `Parent route is required for non-root routes (path: ${pathDef.routeDef.path})`
      );
    }

    const route = createRoute({
      getParentRoute: () => parentRoute,
      path: pathDef.routeDef.path,
      component: pathDef.routeDef.Component as any,
    });

    route.addChildren(
      Object.values(pathDef.children).map((child) =>
        toTanStackRoute(child, route)
      )
    );

    return route;
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
  const routeTree = useMemo(() => {
    const rootRoute = createRootRoute({
      component: () => (
        <>
          <Outlet />
          <TanStackRouterDevtools />
        </>
      ),
    });

    const output = [];
    for (const route of Object.values(routes)) {
      output.push(toTanStackRoute(route));
    }

    output.push(
      createRoute({
        getParentRoute: () => rootRoute,
        path: "$",
        component: (notfound || NotFoundComponent) as any,
      })
    );

    rootRoute.addChildren(output);
    return rootRoute;
  }, [routes]);

  // const router =
  //   platform === "native"
  //     ? createMemoryRouter(config)
  //     : createBrowserRouter(config);

  const router = createRouter({
    routeTree,
  });

  return <RouterProvider router={router} />;
};
