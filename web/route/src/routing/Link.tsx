import React from "react";
import { ArgSchema, ArgType, PathDefChildren } from "./route";
import { PathDef } from "./route";
import { useNavigate } from "@tanstack/react-router";

/**
 * This file contains all helper to dealing with Links and Navigation in the application so that we can handle it easier in different platforms
 */

export const InternalLink = <
  U extends Record<string, keyof ArgType>,
  Q extends Record<string, keyof ArgType>
>(
  props: {
    path: PathDef<U, Q, PathDefChildren>;
    openInNewPage?: boolean;
    urlArgs: ArgSchema<U>;
    queryArgs: ArgSchema<Q>;
  } & Omit<React.HTMLProps<HTMLAnchorElement>, "onClick">
) => {
  const navigate = useNavigate();

  const { path, urlArgs, queryArgs, children, openInNewPage, ...restprops } =
    props;
  const onClick = (e: any) => {
    path
      .path({ urlArgs, queryArgs })
      .mouseClickNavigationHandler(navigate, e, openInNewPage);
  };

  return (
    <a
      href={path.getURL({ urlArgs, queryArgs })}
      onClick={onClick}
      {...restprops}
    >
      {children}
    </a>
  );
};

export const ExternalLink = ({
  href,
  openInNewPage = false,
  children,
  onCtrlClick,
  ...restprops
}: {
  href?: string;
  openInNewPage?: boolean;
  onCtrlClick?: () => void;
} & Omit<React.HTMLProps<HTMLAnchorElement>, "href" | "target" | "rel">) => {
  const onClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if ((e.ctrlKey || e.metaKey) && onCtrlClick) {
      // holding ctrl or cmd key, we trigger the action
      e.preventDefault();
      onCtrlClick();
    }
  };

  if (onCtrlClick !== undefined) {
    restprops.onClick = onClick;
  }

  return (
    <a
      href={href}
      target={openInNewPage ? "_blank" : undefined}
      rel="noopener noreferrer"
      {...restprops}
    >
      {children}
    </a>
  );
};
