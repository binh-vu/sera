import { isObjectProperty } from "sera-db";
import { InputInterface } from ".";
import { Select } from "@mantine/core";
import { useMultiLingualString } from "../../misc";
export const EnumInput: React.FC<InputInterface<any>> = ({
  property,
  value,
  onChange,
  freeze = false,
}) => {
  if (isObjectProperty(property) || property.enumType === undefined) {
    throw new Error(
      "Invalid usage of EnumInput. Expect a property of type enum"
    );
  }
  const enumOptions = Object.entries(property.enumType.label).map(
    ([key, label]) => ({
      value: key,
      label: useMultiLingualString(label),
    })
  );
   
  return (
    <Select
      data={enumOptions}
      value={value}
      onChange={onChange}
      disabled={freeze}
    />
  );
};
