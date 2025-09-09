import { createContext } from "react";

type LinkComponent = React.FunctionComponent<{
  to: any;
  params: { id: string | number };
  openInNewPage?: boolean;
  children: React.ReactNode;
}>;

export const ExternalComponentContext = createContext<{
  link: LinkComponent;
}>({ link: () => null });

export const ExternalComponentProvider = ({
  link,
  children,
}: {
  link: LinkComponent;
  children: React.ReactNode;
}) => {
  return (
    <ExternalComponentContext.Provider value={{ link }}>
      {children}
    </ExternalComponentContext.Provider>
  );
};
