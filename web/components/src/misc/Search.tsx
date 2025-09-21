import { TextInput } from "@mantine/core";
import { IconAdjustmentsHorizontal, IconSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";

import { debounce } from "throttle-debounce";

interface SearchInputProps {
  // The current value of the search input
  query?: string;
  // Callback when the query changes
  onChange: (query: string) => void;
  // Debounce time in milliseconds
  debounceTime?: number;
}

export const SearchInput = ({
  query,
  onChange,
  debounceTime = 250,
}: SearchInputProps) => {
  const [value, setValue] = useState(query);

  const debouncedOnChange = useMemo(() => {
    return debounce(
      debounceTime,
      (query: string) => {
        onChange(query);
      },
      { atBegin: false }
    );
  }, [debounceTime, onChange]);

  return (
    <TextInput
      flex={1}
      label="Search"
      placeholder="Search..."
      leftSection={<IconSearch size={16} stroke={1.5} />}
      rightSection={<IconAdjustmentsHorizontal size={16} stroke={1.5} />}
      value={value}
      onChange={(e) => {
        setValue(e.target.value);
        debouncedOnChange(e.target.value);
      }}
    />
  );
};
