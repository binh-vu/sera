import dayjs from "dayjs";
import { InputInterface } from ".";
import { DatePickerInput } from "@mantine/dates";

export const DateInput: React.FC<InputInterface<Date | undefined>> = ({
  property,
  value,
  onChange,
  freeze = false,
}) => {
  return (
    <DatePickerInput
      id={property.tsName}
      value={value || null}
      onChange={(date) => {
        onChange(
          date === null ? undefined : dayjs(date).startOf("day").toDate()
        );
      }}
      valueFormat="YYYY MMM DD"
      placeholder="Pick date range"
      clearable={true}
      popoverProps={{ withinPortal: false }}
      flex={1}
      disabled={freeze}
    />
  );
};
