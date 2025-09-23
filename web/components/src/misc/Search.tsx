import { TextInput } from "@mantine/core";
import {
  IconAdjustmentsHorizontal,
  IconKeyboard,
  IconSearch,
} from "@tabler/icons-react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { MultiLingualString as MLS } from "sera-db";
import { debounce } from "throttle-debounce";
import { LocaleContext } from "./Locale";

interface SearchInputProps {
  // The current value of the search input
  query?: string;
  // Callback when the query changes
  onChange: (query: string) => void;
  // Debounce time in milliseconds
  debounceTime?: number;
  // Customizable search text in the placeholder, this goes before the searchField
  searchText?: MLS;
  // Displaying the field being searched in the placeholder
  searchField?: MLS;
}

const keyboardIcon = <IconKeyboard size={16} stroke={1.5} />;
const searchIcon = <IconSearch size={16} stroke={1.5} />;
const DEFAULT_SEARCH_TEXT: MLS = {
  lang2value: {
    en: "Search By",
    vi: "Tìm Kiếm Theo",
  },
  lang: "en",
};

export const SearchComponentContext = createContext({
  hasAdvancedSearch: false,
  setHasAdvancedSearch: (value: boolean) => {},
  isAdvancedSearchOpen: false,
  toggleAdvancedSearch: () => {},
});

export const SeraSearch = (props: {
  hasAdvancedSearch?: boolean;
  children: React.ReactNode;
}) => {
  const [hasAdvancedSearch, setHasAdvancedSearch] = useState(
    props.hasAdvancedSearch || false
  );
  const [isAdvancedSearchOpen, setIsAdvancedSearchOpen] = useState(false);

  return (
    <SearchComponentContext.Provider
      value={{
        hasAdvancedSearch,
        setHasAdvancedSearch,
        isAdvancedSearchOpen,
        toggleAdvancedSearch: () => {
          setIsAdvancedSearchOpen(!isAdvancedSearchOpen);
        },
      }}
    >
      {props.children}
    </SearchComponentContext.Provider>
  );
};

/// An input component for full-text search with debounce functionality.
export const SearchInput = ({
  query,
  onChange,
  debounceTime = 250,
  searchText,
  searchField,
}: SearchInputProps) => {
  const [value, setValue] = useState(query);
  const [isDelaying, setIsDelaying] = useState(false);
  const locale = useContext(LocaleContext);
  const { hasAdvancedSearch, toggleAdvancedSearch } = useContext(
    SearchComponentContext
  );

  // Create a debounced version of the onChange handler
  const debouncedOnChange = useMemo(() => {
    return debounce(
      debounceTime,
      (query: string) => {
        setIsDelaying(false);
        onChange(query);
      },
      { atBegin: false }
    );
  }, [debounceTime, onChange]);

  // Handle input change with debounce
  const onQueryChange = useMemo(() => {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setValue(e.target.value);
      setIsDelaying(true);
      debouncedOnChange(e.target.value);
    };
  }, [setValue, setIsDelaying, debouncedOnChange]);

  if (searchText === undefined && searchField !== undefined) {
    searchText = DEFAULT_SEARCH_TEXT;
  }

  let placeholder = "";
  if (searchText !== undefined) {
    placeholder =
      searchText.lang2value[locale.language] ||
      searchText.lang2value[searchText.lang];
  }

  if (searchField !== undefined) {
    if (placeholder.length > 0) placeholder += " ";
    placeholder +=
      searchField.lang2value[locale.language] ||
      searchField.lang2value[searchField.lang];
  }

  return (
    <TextInput
      flex={1}
      label="Search"
      placeholder={placeholder}
      leftSection={isDelaying ? keyboardIcon : searchIcon}
      rightSection={
        hasAdvancedSearch && (
          <IconAdjustmentsHorizontal
            size={16}
            stroke={1.5}
            cursor={"pointer"}
            onClick={toggleAdvancedSearch}
          />
        )
      }
      value={value}
      onChange={onQueryChange}
    />
  );
};

export const SearchPanel = ({}: {
  // props: (Data)
}) => {
  const { setHasAdvancedSearch, isAdvancedSearchOpen } = useContext(
    SearchComponentContext
  );

  useEffect(() => {
    setHasAdvancedSearch(true);
  }, []);

  if (!isAdvancedSearchOpen) {
    return <></>;
  }

  return <div>SearchPanel</div>;
};
