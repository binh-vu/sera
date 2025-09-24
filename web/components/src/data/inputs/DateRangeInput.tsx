import dayjs from "dayjs";
import { InputInterface } from ".";
import { DatePickerInput } from "@mantine/dates";

export const DateRangeInput: React.FC<
  InputInterface<{ from?: Date; to?: Date } | undefined>
> = ({ property, value, onChange }) => {
  return (
    <DatePickerInput
      id={property.tsName}
      type="range"
      value={[value?.from || null, value?.to || null]}
      onChange={(dateRange) => {
        onChange({
          from:
            dateRange[0] === null
              ? undefined
              : dayjs(dateRange[0]).startOf("day").toDate(),
          to:
            dateRange[1] === null
              ? undefined
              : dayjs(dateRange[1]).endOf("day").toDate(),
        });
      }}
      placeholder="Pick date range"
      clearable={true}
      popoverProps={{ withinPortal: false }}
    />
  );
};
