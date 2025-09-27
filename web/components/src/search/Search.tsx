import { Popover, TextInput } from "@mantine/core";
import {
  IconAdjustmentsHorizontal,
  IconKeyboard,
  IconSearch,
} from "@tabler/icons-react";
import { useContext, useMemo, useState } from "react";

import { MultiLingualString as MLS } from "sera-db";
import { debounce } from "throttle-debounce";
import { LocaleContext } from "../misc/Locale";
import { SearchForm, SearchFormProps } from "./SearchForm";

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

  // advanced search configuration
  advancedSearch?: SearchFormProps;
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

/// An search component for full-text search with debounce functionality.
export const SeraSearch = ({
  query,
  onChange,
  debounceTime = 250,
  searchText,
  searchField,
  advancedSearch,
}: SearchInputProps) => {
  const locale = useContext(LocaleContext);

  // State to hold the current search input value
  // There is a slight problem with query different from the value
  // that when the query prop changes from outside, it does not
  // synchronize with the value state. If we try to synchronize it
  // with useEffect, then we will have problem when the user is typing
  // and the query prop changes, the input will be reset. So we need to
  // somehow only synchronize it when the query prop changes from outside
  // via external means such as URL change. This is a bit tricky and
  // haven't addressed yet.
  const [value, setValue] = useState(query);

  // State to indicate if we are in the debounce delay period
  // So that we can show a keyboard icon to indicate that the input is being processed
  const [isDelaying, setIsDelaying] = useState(false);

  // State to control the visibility of the advanced search popover
  // We use a timestamp to prevent immediate reopening when clicking the icon
  const [opened, setOpened] = useState([false, Date.now()] as [
    boolean,
    number
  ]);

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

  // if advanced search is not provided, just return a simple text input
  if (advancedSearch === undefined) {
    return (
      <TextInput
        flex={1}
        label="Search"
        placeholder={placeholder}
        leftSection={isDelaying ? keyboardIcon : searchIcon}
        value={value}
        onChange={onQueryChange}
      />
    );
  }

  // otherwise, return the text input with advanced search popover
  return (
    <Popover
      width="target"
      trapFocus={true}
      position="bottom"
      withArrow={true}
      shadow="md"
      opened={opened[0]}
      onDismiss={() => {
        setOpened([false, Date.now()]);
      }}
    >
      <Popover.Target>
        <TextInput
          flex={1}
          label="Search"
          placeholder={placeholder}
          leftSection={isDelaying ? keyboardIcon : searchIcon}
          rightSection={
            <IconAdjustmentsHorizontal
              size={16}
              stroke={1.5}
              cursor={"pointer"}
              style={{
                position: "relative",
              }}
              onClick={() => {
                if (opened[1] + 200 >= Date.now()) {
                  // workaround to close the popover when clicking
                  // the icon again because mantine still detects that
                  // clicking the icon is outside the popover
                  return;
                }
                setOpened([true, Date.now()]);
              }}
            />
          }
          value={value}
          onChange={onQueryChange}
        />
      </Popover.Target>
      <Popover.Dropdown>
        <SearchForm
          db={advancedSearch.db}
          properties={advancedSearch.properties}
          layout={advancedSearch.layout}
          styles={advancedSearch.styles}
          className={advancedSearch.className}
          onChange={advancedSearch.onChange}
          queryConditions={advancedSearch.queryConditions}
        />
      </Popover.Dropdown>
    </Popover>
  );
};
