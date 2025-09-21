import { useContext, useMemo } from "react";
import { DisplayInterface } from ".";
import { Text } from "@mantine/core";
import { LocaleContext } from "../../misc";

function formatDate(locale: Intl.Locale, value: Date): string {
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
}

export const DateTimeDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const formattedDt = useMemo(() => {
    const hours = value.getHours().toString().padStart(2, "0");
    const minutes = value.getMinutes().toString().padStart(2, "0");
    const seconds = value.getSeconds().toString().padStart(2, "0");

    return formatDate(locale, value) + `${hours}:${minutes}:${seconds}`;
  }, [locale, value]);

  return <Text size="sm">{formattedDt}</Text>;
};

export const DateDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const formattedDt = useMemo(() => formatDate(locale, value), [locale, value]);

  return <Text size="sm">{formattedDt}</Text>;
};

export const DateTimeHideTimeDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const [formattedDate, formattedTime] = useMemo(() => {
    const date = formatDate(locale, value);
    const hours = value.getHours().toString().padStart(2, "0");
    const minutes = value.getMinutes().toString().padStart(2, "0");
    const seconds = value.getSeconds().toString().padStart(2, "0");

    return [date, `${hours}:${minutes}:${seconds}`];
  }, [locale, value]);

  return (
    <Text size="sm" title={formattedTime}>
      {formattedDate}
    </Text>
  );
};
