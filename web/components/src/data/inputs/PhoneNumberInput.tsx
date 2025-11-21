import React, { useMemo, useState } from "react";
import { IconSearch } from "@tabler/icons-react";
import { IMaskInput } from "react-imask";
import { MultiLingualString as MLS } from "sera-db";
import {
  Combobox,
  Grid,
  Group,
  Input,
  InputBase,
  Text,
  useCombobox,
} from "@mantine/core";
import {
  CountryFlag,
  CountryFlagComponent,
  countryFlags,
} from "../../misc/CountryFlag";
import { MultiLingualString } from "../../misc";
import { Trie } from "../../utils";

const leadingZeroMessage: MLS = {
  lang2value: {
    en: "The leading zero is not necessary in international phone number format. For example, if your phone number is 0123456789, you should enter it as 123-456-789.",
    vi: "Số 0 đầu tiên không cần thiết trong định dạng điện thoại quốc tế. Ví dụ, nếu số điện thoại của bạn là 0123456789, bạn nên nhập nó là 123-456-789.",
  },
  lang: "en",
};

const noCountryCodeMessage: MLS = {
  lang2value: {
    en: "No valid country code found.",
    vi: "Không tìm thấy mã quốc gia hợp lệ. ",
  },
  lang: "en",
};

interface CountryData {
  name: string;
  flags: CountryFlag[];
}

const COUNTRIES: Record<string, CountryData> = {
  "84": {
    name: "Vietnam",
    flags: [countryFlags.VN],
  },
  "1": {
    name: "US, Canada",
    flags: [countryFlags.US, countryFlags.CA],
  },
  "61": {
    name: "Australia",
    flags: [countryFlags.AU],
  },
  "81": {
    name: "Japan",
    flags: [countryFlags.JP],
  },
  "44": {
    name: "UK",
    flags: [countryFlags.UK],
  },
  "33": {
    name: "France",
    flags: [countryFlags.FR],
  },
  "49": {
    name: "Germany",
    flags: [countryFlags.DE],
  },
  "91": {
    name: "India",
    flags: [countryFlags.IN],
  },
  "55": {
    name: "Brazil",
    flags: [countryFlags.BR],
  },
  "34": {
    name: "Spain",
    flags: [countryFlags.ES],
  },
  "39": {
    name: "Italy",
    flags: [countryFlags.IT],
  },
  "64": {
    name: "New Zealand",
    flags: [countryFlags.NZ],
  },
  "52": {
    name: "Mexico",
    flags: [countryFlags.MX],
  },
  "86": {
    name: "China",
    flags: [countryFlags.CN],
  },
  "855": {
    name: "Cambodia",
    flags: [countryFlags.CAM],
  },
};

const findCountryCodePrefix = (
  value: string,
  countryCodeTrie: Trie
): { match: string; remaining: string } => {
  if (value === "") {
    return { match: "84", remaining: "" };
  }
  const digits = value.replace(/[^\d]/g, "");
  const result = countryCodeTrie.findLongestPrefix(digits);

  //  Throw error if no match found
  if (result.match === "") {
    throw new Error(`No valid country code found for phone number: ${value}`);
  }

  return result;
};

// Render country flags in the dropdown field.
const TelephoneCountryCode = ({ value }: { value: string }) => {
  const countryData = COUNTRIES[value];
  if (countryData === undefined) return undefined;

  return (
    <Group gap="sm" wrap="nowrap" align="center">
      <Text size="sm">+{value}</Text>
      <Group gap={4} wrap="nowrap">
        {countryData.flags.map((flag, index) => (
          <CountryFlagComponent key={index} flag={flag} />
        ))}
      </Group>
    </Group>
  );
};

export interface PhoneNumberInputProps {
  id: string;
  value: string;
  type: string;
  onChange: (e: { target: { value: string } }) => void;
  error?: boolean | React.ReactNode;
  disabled?: boolean;
  readonly?: boolean;
}

export const PhoneNumberInput: React.FC<PhoneNumberInputProps> = ({
  value,
  onChange,
  error,
  id,
  disabled = false,
  readonly = false,
}) => {
  const [search, setSearch] = useState("");
  const [showLeadingZeroWarning, setShowLeadingZeroWarning] = useState(false);
  const [countryCode, setCountryCode] = useState("");
  const [showNoCountryCodeError, setShowNoCountryCodeError] = useState(false);

  const countryCodeTrie = useMemo(() => {
    const trie = new Trie();
    Object.keys(COUNTRIES).forEach((code) => {
      trie.insert(code);
    });
    return trie;
  }, [COUNTRIES]);

  const { rawInput } = useMemo(() => {
    try {
      const { match, remaining } = findCountryCodePrefix(
        value,
        countryCodeTrie
      );
      setCountryCode(match);
      setShowNoCountryCodeError(false);
      return {
        rawInput: remaining,
      };
    } catch (error) {
      // Set the initial value for the countrycode when the value is empty or undefined.
      // This allows to handle the case when the user add new record and the phone number field is currently undefined.
      if (value === "" || value === undefined) {
        setCountryCode("84");
        setShowNoCountryCodeError(false);
        return {
          rawInput: "",
        };
      }
      setShowNoCountryCodeError(true);
      setCountryCode("");
      return {
        rawInput: value,
      };
    }
  }, [value]);

  const combobox = useCombobox({
    onDropdownClose: () => {
      combobox.resetSelectedOption();
      setSearch("");
    },
    onDropdownOpen: () => {
      combobox.updateSelectedOptionIndex("active");
    },
  });

  // List of country codes for filtering in the combobox
  const countryCodes = useMemo(() => Object.keys(COUNTRIES), [COUNTRIES]);

  const formatPhoneNumber = (digits: string, selectedCountryCode: string) => {
    if (digits === undefined) {
      return `+${selectedCountryCode}`;
    }

    const cleanDigits = digits.replace(/[^\d]/g, "");

    if (cleanDigits.length === 0) {
      return `+${selectedCountryCode}`;
    }

    if (cleanDigits.startsWith("0")) {
      setShowLeadingZeroWarning(true);
      return `+${selectedCountryCode}${cleanDigits}`;
    } else {
      setShowLeadingZeroWarning(false);
      return `+${selectedCountryCode}${cleanDigits}`;
    }
  };

  // Filter countries based on search input - matches either country name/label or country code
  const filteredOptions = useMemo(() => {
    return countryCodes.filter((code) => {
      const country = COUNTRIES[code];
      return (
        country.name.toLowerCase().includes(search.toLowerCase()) ||
        code.includes(search)
      );
    });
  }, [search, countryCodes]);

  // Convert filtered country data into Combobox option components for rendering in dropdown
  const options = useMemo(() => {
    return filteredOptions.map((code, index) => (
      <Combobox.Option value={code} key={index}>
        <TelephoneCountryCode value={code} />
      </Combobox.Option>
    ));
  }, [filteredOptions]);

  return (
    <div>
      <Grid gutter="xs">
        <Grid.Col>
          <Group gap={5}>
            <Combobox
              store={combobox}
              position="top-start"
              onOptionSubmit={(val) => {
                setSearch("");
                combobox.closeDropdown();
                onChange({
                  target: { value: formatPhoneNumber(rawInput, val) },
                });
              }}
              disabled={disabled}
            >
              <Combobox.Target>
                <InputBase
                  component="button"
                  type="button"
                  pointer
                  rightSection={<Combobox.Chevron />}
                  onClick={() => !disabled && combobox.toggleDropdown()}
                  rightSectionPointerEvents="none"
                  w={110}
                  disabled={disabled}
                >
                  <TelephoneCountryCode value={countryCode} />
                </InputBase>
              </Combobox.Target>

              <Combobox.Dropdown>
                <Combobox.Search
                  leftSection={<IconSearch size={14} stroke={1.5} />}
                  placeholder="....."
                  value={search}
                  onChange={(event) => setSearch(event.currentTarget.value)}
                  disabled={disabled}
                />
                <Combobox.Options>
                  {options.length > 0 ? (
                    options
                  ) : (
                    <Combobox.Empty>
                      <Text size="sm">Nothing found</Text>
                    </Combobox.Empty>
                  )}
                </Combobox.Options>
              </Combobox.Dropdown>
            </Combobox>
            {countryCode === "" ? (
              <Input
                id={id}
                value={rawInput}
                type={"phone_number"}
                onChange={(e) => {
                  onChange({ target: { value: e.target.value } });
                }}
                error={error}
                flex={1}
                disabled={disabled}
                readOnly={readonly}
              />
            ) : (
              <Input
                id={id}
                value={rawInput}
                type={"phone_number"}
                onAccept={(val: string) => {
                  const digits = val.replace(/[^\d]/g, "");
                  const nextValue = formatPhoneNumber(digits, countryCode);
                  if (nextValue === value) {
                    return;
                  }
                  onChange({
                    target: { value: nextValue },
                  });
                }}
                component={IMaskInput}
                mask={`000-000-0000`}
                error={error}
                flex={1}
                disabled={disabled}
                readOnly={readonly}
              />
            )}
          </Group>
        </Grid.Col>
      </Grid>
      {(showLeadingZeroWarning ||
        showNoCountryCodeError ||
        (error && typeof error === "string")) && (
        <Grid gutter="xs">
          <Grid.Col>
            <Input.Error>
              {showLeadingZeroWarning ? (
                <MultiLingualString value={leadingZeroMessage} />
              ) : showNoCountryCodeError ? (
                <MultiLingualString value={noCountryCodeMessage} />
              ) : (
                error
              )}
            </Input.Error>
          </Grid.Col>
        </Grid>
      )}
    </div>
  );
};
