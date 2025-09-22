import { TextInput } from "@mantine/core";
import {
  IconAdjustmentsHorizontal,
  IconKeyboard,
  IconSearch,
} from "@tabler/icons-react";
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

const keyboardIcon = <IconKeyboard size={16} stroke={1.5} />;
const searchIcon = <IconSearch size={16} stroke={1.5} />;

export const SearchInput = ({
  query,
  onChange,
  debounceTime = 250,
}: SearchInputProps) => {
  const [value, setValue] = useState(query);
  const [isEntering, setIsEntering] = useState(false);

  const debouncedOnChange = useMemo(() => {
    return debounce(
      debounceTime,
      (query: string) => {
        setIsEntering(false);
        onChange(query);
      },
      { atBegin: false }
    );
  }, [debounceTime, onChange]);

  const updateValue = useMemo(() => {
    return (query: string) => {
      setValue(query);
      setIsEntering(true);
    };
  }, [setValue, setIsEntering]);

  return (
    <TextInput
      flex={1}
      label="Search"
      placeholder="Search..."
      leftSection={isEntering ? keyboardIcon : searchIcon}
      rightSection={<IconAdjustmentsHorizontal size={16} stroke={1.5} />}
      value={value}
      onChange={(e) => {
        updateValue(e.target.value);
        debouncedOnChange(e.target.value);
      }}
    />
  );
};
