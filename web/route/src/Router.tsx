import { useMemo } from "react";
import { IRoute, PathDef, ReactComponent } from "./routing";
import { NotFoundComponent } from "./components";
import { PathDefChildren } from "./routing/route";
import {
  Outlet,
  RouterProvider,
  createRouter,
  createRoute,
  createRootRoute,
  Route,
} from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

function toTanStackRoute(
  route: IRoute<any, any, PathDefChildren>,
  parentRoute: Route<any, any>
): Route<any, any> {
  const pathDef = route instanceof PathDef ? route : route.path;

  if (pathDef.routeDef.path === "/") {
    return createRoute({
      path: "/",
      getParentRoute: () => parentRoute,
      component: pathDef.routeDef.Component as any,
    });
  } else {
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
  notfound,
}: {
  routes: {
    [name: string]: IRoute<any, any, PathDefChildren>;
  };
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
      output.push(toTanStackRoute(route, rootRoute));
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

  const router = createRouter({
    routeTree,
  });

  return <RouterProvider router={router} />;
};
