import { InputInterface } from ".";
import { Input } from "@mantine/core";

export const BooleanInput: React.FC<InputInterface<boolean>> = ({ property, value, onChange }) => {
  return (
    <Input
      id={property.name}
      type="checkbox"
      checked={value}
      onChange={(e) => {
        const newValue = e.target.checked;
        onChange(newValue);
      }}
    />
  );
};
