import { InputInterface } from ".";
import { Input } from "@mantine/core";

export const NumberInput: React.FC<InputInterface<number | undefined>> = ({
  property,
  value,
  onChange,
  freeze = false,
}) => {
  return (
    <Input
      id={property.name}
      type="number"
      value={value}
      onChange={(e) => {
        const newValue = e.target.value;
        if (newValue === "") {
          onChange(undefined);
        } else {
          onChange(Number(newValue));
        }
      }}
      disabled={freeze}
    />
  );
};
