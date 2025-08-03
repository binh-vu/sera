import { DisplayInterface } from ".";
import { Text } from "@mantine/core";

export const TextDisplay = ({ value }: DisplayInterface<string>) => {
  return <Text size="sm">{value}</Text>;
};
