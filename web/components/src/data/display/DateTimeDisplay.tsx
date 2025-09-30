import { useContext, useMemo } from "react";
import { DisplayInterface } from ".";
import { Text } from "@mantine/core";
import { LocaleContext } from "../../misc";

export function formatDate(locale: Intl.Locale, value: Date): string {
  return value.toLocaleDateString(locale.baseName, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function formatDateTime(
  locale: Intl.Locale,
  value: Date,
  withSeconds: boolean = true
): string {
  const hours = value.getHours().toString().padStart(2, "0");
  const minutes = value.getMinutes().toString().padStart(2, "0");
  const seconds = value.getSeconds().toString().padStart(2, "0");

  if (withSeconds) {
    return formatDate(locale, value) + ` ${hours}:${minutes}:${seconds}`;
  }
  return formatDate(locale, value) + ` ${hours}:${minutes}`;
}

export const DateTimeDisplay = ({ value }: DisplayInterface<Date>) => {
  const locale = useContext(LocaleContext);

  const formattedDt = useMemo(
    () => formatDateTime(locale, value),
    [locale, value]
  );

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
