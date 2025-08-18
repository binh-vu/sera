import { isObjectProperty } from "sera-db";
import { DisplayInterface } from ".";
import { Text } from "@mantine/core";
import { MultiLingualString } from "../../basic";

export const EnumDisplay = ({
  nestedProperty,
  property,
  value,
}: DisplayInterface<any>) => {
  const prop = nestedProperty || property;
  if (isObjectProperty(prop) || prop.enumType === undefined) {
    throw new Error(
      "Invalid usage of EnumDisplay. Expect a property of type enum"
    );
  }

  return (
    <Text size="sm">
      <MultiLingualString value={prop.enumType.label[value]} />
    </Text>
  );
};
