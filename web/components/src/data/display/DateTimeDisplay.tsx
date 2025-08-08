import { useContext, useMemo } from "react";
import { DisplayInterface } from ".";
import { Text } from "@mantine/core";
import { LocaleContext } from "../../basic";

export const DateTimeDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const formattedDt = useMemo(() => {
    const day = value.getDate().toString().padStart(2, "0");
    const month = (value.getMonth() + 1).toString().padStart(2, "0");
    const year = value.getFullYear();
    const hours = value.getHours().toString().padStart(2, "0");
    const minutes = value.getMinutes().toString().padStart(2, "0");
    const seconds = value.getSeconds().toString().padStart(2, "0");

    if (locale.baseName === "en-US") {
      return `${month}/${day}/${year} ${hours}:${minutes}:${seconds}`;
    } else if (locale.baseName === "vi-VN") {
      return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
    } else {
      return `${month}/${day}/${year} ${hours}:${minutes}:${seconds}`;
    }
  }, [locale, value]);

  return <Text size="sm">{formattedDt}</Text>;
};

export const DateDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const formattedDt = useMemo(() => {
    const day = value.getDate().toString().padStart(2, "0");
    const month = (value.getMonth() + 1).toString().padStart(2, "0");
    const year = value.getFullYear();

    if (locale.baseName === "en-US") {
      return `${month}/${day}/${year}`;
    } else if (locale.baseName === "vi-VN") {
      return `${day}/${month}/${year}`;
    } else {
      return `${month}/${day}/${year}`;
    }
  }, [locale, value]);

  return <Text size="sm">{formattedDt}</Text>;
};
