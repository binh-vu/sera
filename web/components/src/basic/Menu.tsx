import { useEffect, useMemo, useState } from "react";
import { IconChevronRight } from "@tabler/icons-react";
import { useLocation, useNavigate } from "sera-route";
import { NoArgsPathDef } from "sera-route";
import { NavLink } from "@mantine/core";
import { Trie } from "../misc";

type MenuKey = string;

export enum Permission {
  /// Allow access to the menu item
  Allow,
  /// Deny access to the menu item
  Denied,
  /// Pending access to the menu item, e.g., waiting for a user role to be set
  Pending,
}

/**
 * Specialized Trie data structure for efficient menu route matching and navigation.
 *
 * Provides O(m) lookup time for finding the best matching menu item based on URL paths,
 * where m is the length of the path.
 */
export class MenuTrie extends Trie {
  private pathToKey: Map<string, string> = new Map();

  /**
   * Normalizes a URL path by removing trailing slashes
   *
   * @param path - The path which is an URL string to normalize
   * @returns The normalized path without trailing slash, except for root "/"
   */
  private normalizePath(path: string): string {
    // Keep root path as-is
    if (path === "/") return "/";

    // Remove trailing slash using regex: /\/$/ matches slash at end of string
    const cleanPath = path.replace(/\/$/, "");
    return cleanPath;
  }

  /**
   * Inserts an url path into the trie and associates it with a menu key.
   *
   * @param path - The URL path to store (e.g., "/admin/users")
   * @param menuKey - The menu key to associate with this path
   */
  insertRoute(path: string, menuKey: string): void {
    const normalizedPath = this.normalizePath(path);

    this.insert(normalizedPath);

    this.pathToKey.set(normalizedPath, menuKey);
  }

  /**
   * Finds the menu key associated with the longest matching route prefix
   *
   * @param route - The URL to match against stored menu url paths
   * @returns The menu key if a valid prefix match is found, undefined otherwise
   */
  findMatchingKey(route: string): string | undefined {
    const normalizedRoute = this.normalizePath(route);

    const result = this.findLongestPrefix(normalizedRoute);

    /// If we found a match, check if it's a valid prefix by checking the remaining part and the match
    if (result.match && this.pathToKey.has(result.match)) {
      const isValidPrefix =
        normalizedRoute === result.match ||
        result.remaining.startsWith("/") ||
        result.remaining === "";

      if (isValidPrefix) {
        return this.pathToKey.get(result.match)!;
      }
    }

    return undefined;
  }
}

export interface MenuRoute<R> {
  path: NoArgsPathDef<any>;
  role: R;
}

export interface SeraMenuItem<R> {
  key: MenuKey;
  label: React.ReactElement | string;
  icon?: React.ReactElement;
  route?: MenuRoute<R>;
  children?: SeraMenuItem<R>[];
}

/// Build a map of key to item and key to route
/// to help retrieve item from key and route from key
export function buildMenuItemIndex<R>(items: SeraMenuItem<R>[]): {
  key2item: Record<MenuKey, SeraMenuItem<R>>;
  key2fullpath: Record<MenuKey, MenuKey[]>;
  key2route: { [key: MenuKey]: MenuRoute<R> };
} {
  const key2item: Record<MenuKey, SeraMenuItem<R>> = {};
  const key2fullpath: Record<MenuKey, MenuKey[]> = {};
  const key2route: { [key: MenuKey]: MenuRoute<R> } = {};

  const traverseItems = (
    items: SeraMenuItem<R>[],
    parentKeyPath: MenuKey[] = []
  ) => {
    items.forEach((item) => {
      const currentKeyPath = [...parentKeyPath, item.key];
      key2item[item.key] = item;
      key2fullpath[item.key] = currentKeyPath;

      if (item.route !== undefined) {
        key2route[item.key] = item.route;
      }

      if (item.children !== undefined && item.children.length > 0) {
        traverseItems(item.children, currentKeyPath);
      }
    });
  };

  traverseItems(items);

  return { key2item, key2fullpath, key2route };
}

/// Initialize the menu trie from the menu items
function createMenuTrie<R>(items: SeraMenuItem<R>[]): MenuTrie {
  const menuTrie = new MenuTrie();

  const traverseItems = (items: SeraMenuItem<R>[]) => {
    items.forEach((item) => {
      if (item.route !== undefined) {
        const routePath = item.route.path.getURL();
        menuTrie.insertRoute(routePath, item.key);
      }

      if (item.children !== undefined && item.children.length > 0) {
        traverseItems(item.children);
      }
    });
  };

  traverseItems(items);
  return menuTrie;
}

/// Filter the items based on the permission, so that we only show the items
/// that the user has permission to access
export function filterAllowedItems<R>(
  items: SeraMenuItem<R>[],
  checkPermission: (role: R) => Permission
): SeraMenuItem<R>[] {
  return items
    .map((item) => {
      // if the item has a route, we will check the permission
      if (item.route !== undefined) {
        return checkPermission(item.route.role) === Permission.Allow
          ? item
          : null;
      }

      // if the item is a group, we will check the children
      if (item.children !== undefined) {
        const filteredChildren = item.children.filter((child) => {
          if (child.route !== undefined) {
            return checkPermission(child.route.role) === Permission.Allow;
          }
          return true;
        });

        // Only include item if it has children
        return filteredChildren.length > 0
          ? { ...item, children: filteredChildren }
          : null;
      }

      // if the item does not have a route, we will just return it
      return item;
    })
    .filter((item) => item !== null) as SeraMenuItem<R>[];
}

/// Is an observer component because of `useCheckPermission` that uses `useStores`
export const SeraVerticalMenu = <R,>(props: {
  items: SeraMenuItem<R>[];
  checkPermission: (role: R) => Permission;
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  /// State to manage keys that are open on mouse hover
  const [hoverOpenKeys, setHoverOpenKeys] = useState<Set<string>>(new Set());
  /// State to manage keys that are open on click
  const [clickOpenKeys, setClickOpenKeys] = useState<Set<string>>(new Set());
  /// State to manage the currently selected key to highlight the active menu item
  const [selectedKey, setSelectedKey] = useState<string>();

  // filter the items based on the permission, so that we only show the items
  // that the user has permission to access
  const allowedItems = useMemo(() => {
    return filterAllowedItems(props.items, props.checkPermission);
  }, [props.items, props.checkPermission]);

  const menuTrie = useMemo(() => createMenuTrie(props.items), [props.items]);

  // construct indices to help retrieve item from key and key from route
  const { key2fullpath, key2route } = useMemo(
    () => buildMenuItemIndex(allowedItems),
    [allowedItems]
  );

  // get the selected keys from active routes
  useEffect(() => {
    const currentPath = location.pathname;
    const activateKey = menuTrie.findMatchingKey(currentPath);
    if (activateKey !== undefined) {
      setClickOpenKeys(new Set(key2fullpath[activateKey]));
      setSelectedKey(activateKey);
    }
  }, [location, key2route]);

  const menu = useMemo(() => {
    function genNavLink(
      item: SeraMenuItem<R>,
      level: number
    ): React.ReactElement {
      const hasChildren =
        item.children !== undefined && item.children.length > 0;

      // If the item has children, return a container with NavLink and children so the mouse events can be handled
      if (hasChildren) {
        return (
          <div
            key={`container-${item.key}`}
            onMouseEnter={() => {
              if (!clickOpenKeys.has(item.key)) {
                setHoverOpenKeys((prevOpenKeys) => {
                  const newOpenKeys = new Set(prevOpenKeys);
                  newOpenKeys.add(item.key);
                  return newOpenKeys;
                });
              }
            }}
            onMouseLeave={() => {
              if (!clickOpenKeys.has(item.key)) {
                setHoverOpenKeys((prevOpenKeys) => {
                  const newOpenKeys = new Set(prevOpenKeys);
                  newOpenKeys.delete(item.key);
                  return newOpenKeys;
                });
              }
            }}
          >
            <NavLink
              key={item.key}
              active={selectedKey === item.key}
              href={item.route?.path.getURL()}
              label={item.label}
              leftSection={item.icon}
              styles={{
                label: { fontSize: "md" },
                root: {
                  borderRadius: "var(--mantine-radius-sm)",
                },
              }}
              ml={
                level === 0
                  ? undefined
                  : level === 1
                  ? "md"
                  : `calc(var(--mantine-spacing-md) * ${level})`
              }
              w="unset"
              rightSection={
                hasChildren ? (
                  <IconChevronRight
                    size={12}
                    stroke={1.5}
                    className="mantine-rotate-rtl"
                  />
                ) : undefined
              }
              opened={
                hoverOpenKeys.has(item.key) || clickOpenKeys.has(item.key)
              }
              onClick={(event) => {
                const isModifiedClick = event.ctrlKey || event.metaKey;

                if (isModifiedClick) {
                  return;
                }
                event.preventDefault();

                setClickOpenKeys((prevClickOpenKeys) => {
                  const newOpenKeys = new Set(prevClickOpenKeys);
                  if (prevClickOpenKeys.has(item.key)) {
                    newOpenKeys.delete(item.key);
                  } else {
                    newOpenKeys.add(item.key);
                  }
                  return newOpenKeys;
                });
              }}
            ></NavLink>
            {(clickOpenKeys.has(item.key) || hoverOpenKeys.has(item.key)) &&
              item.children!.map((child) => genNavLink(child, level + 1))}
          </div>
        );
      } else {
        // If no children, return a simple NavLink
        return (
          <NavLink
            key={item.key}
            active={selectedKey === item.key}
            href={item.route?.path.getURL()}
            label={item.label}
            leftSection={item.icon}
            styles={{
              label: { fontSize: "md" },
              root: {
                borderRadius: "var(--mantine-radius-sm)",
              },
            }}
            ml={
              level === 0
                ? undefined
                : level === 1
                ? "md"
                : `calc(var(--mantine-spacing-md) * ${level})`
            }
            w="unset"
            onClick={(event) => {
              const isModifiedClick = event.ctrlKey || event.metaKey;

              if (isModifiedClick) {
                return;
              }
              event.preventDefault();
              // open the link if it's a leaf node and have a route
              if (item.route != undefined) {
                item.route.path.path().open(navigate);
              }
            }}
          ></NavLink>
        );
      }
    }
    // Generate the menu items recursively
    return allowedItems.map((allowItem) => genNavLink(allowItem, 0));
  }, [allowedItems, selectedKey, clickOpenKeys, hoverOpenKeys, navigate]);

  return <>{menu}</>;
};
