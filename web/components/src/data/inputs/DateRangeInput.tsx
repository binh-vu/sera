import dayjs from "dayjs";
import { InputInterface } from ".";
import { DatePickerInput } from "@mantine/dates";
import { Group } from "@mantine/core";

export const DateRangeInput: React.FC<
  InputInterface<{ from?: Date; to?: Date } | undefined>
> = ({ property, value, onChange }) => {
  return (
    <Group gap="sm" justify="space-between" grow={true}>
      <DatePickerInput
        id={property.tsName}
        value={value?.from || null}
        onChange={(date) => {
          onChange({
            from:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
      />
      <DatePickerInput
        id={property.tsName}
        value={value?.from || null}
        onChange={(date) => {
          onChange({
            from:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
      />
    </Group>
  );
};
