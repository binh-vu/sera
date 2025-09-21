import { TextInput } from "@mantine/core";
import { IconAdjustmentsHorizontal, IconSearch } from "@tabler/icons-react";

export const SearchInput = ({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) => {
  return (
    <TextInput
      flex={1}
      label="Search"
      placeholder="Search..."
      leftSection={<IconSearch size={16} stroke={1.5} />}
      rightSection={<IconAdjustmentsHorizontal size={16} stroke={1.5} />}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
};
