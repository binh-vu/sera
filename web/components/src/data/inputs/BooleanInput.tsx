import { InputInterface } from ".";
import { Checkbox } from "@mantine/core";

export const BooleanInput: React.FC<InputInterface<boolean>> = ({
  property,
  value,
  onChange,
  freeze = false,
}) => {
  return (
    <Checkbox
      id={property.name}
      checked={value}
      onChange={(e) => {
        const newValue = e.target.checked;
        onChange(newValue);
      }}
      disabled={freeze}
    />
  );
};
