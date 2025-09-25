import dayjs from "dayjs";
import { InputInterface } from ".";
import { DatePickerInput } from "@mantine/dates";
import { Flex } from "@mantine/core";

export const DateRangeInput: React.FC<
  InputInterface<{ from?: Date; to?: Date } | undefined>
> = ({ property, value, onChange }) => {
  return (
    <Flex gap="sm" justify="space-between" direction="row" align="center">
      <DatePickerInput
        id={property.tsName}
        value={value?.from || null}
        onChange={(date) => {
          onChange({
            from:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
            to: value?.to,
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
      />
      <span style={{ flexGrow: 0 }}>–</span>
      <DatePickerInput
        id={property.tsName}
        value={value?.to || null}
        onChange={(date) => {
          onChange({
            from: value?.from,
            to: date === null ? undefined : dayjs(date).startOf("day").toDate(),
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
      />
    </Flex>
  );
};
