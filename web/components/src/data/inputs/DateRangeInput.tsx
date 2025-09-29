import dayjs from "dayjs";
import { InputInterface } from ".";
import { DatePickerInput } from "@mantine/dates";
import { Flex } from "@mantine/core";
import { IconCalendar } from "@tabler/icons-react";

export const DateRangeInput: React.FC<
  InputInterface<{ start?: Date; end?: Date } | undefined>
> = ({ property, value, onChange }) => {
  return (
    <Flex gap="sm" justify="space-between" direction="row" align="center">
      <DatePickerInput
        id={property.tsName}
        value={value?.start || null}
        onChange={(date) => {
          onChange({
            start:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
            end: value?.end,
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
        leftSection={<IconCalendar size={16} stroke={1.5} />}
      />
      <span style={{ flexGrow: 0 }}>–</span>
      <DatePickerInput
        id={property.tsName}
        value={value?.end || null}
        onChange={(date) => {
          onChange({
            start: value?.start,
            end:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
        leftSection={<IconCalendar size={16} stroke={1.5} />}
      />
    </Flex>
  );
};

export const DateTimeRangeInput: React.FC<
  InputInterface<{ start?: Date; end?: Date } | undefined>
> = ({ property, value, onChange }) => {
  return (
    <Flex gap="sm" justify="space-between" direction="row" align="center">
      <DatePickerInput
        id={property.tsName}
        value={value?.start || null}
        onChange={(date) => {
          onChange({
            start:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
            end: value?.end,
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
        // withSeconds={true}
        leftSection={<IconCalendar size={16} stroke={1.5} />}
      />
      <span style={{ flexGrow: 0 }}>–</span>
      <DatePickerInput
        id={property.tsName}
        value={value?.end || null}
        onChange={(date) => {
          onChange({
            start: value?.start,
            end:
              date === null ? undefined : dayjs(date).startOf("day").toDate(),
          });
        }}
        valueFormat="YYYY MMM DD"
        placeholder="Pick date range"
        clearable={true}
        popoverProps={{ withinPortal: false }}
        flex={1}
        leftSection={<IconCalendar size={16} stroke={1.5} />}
      />
    </Flex>
  );
};
