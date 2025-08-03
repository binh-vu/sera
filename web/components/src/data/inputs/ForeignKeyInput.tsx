import { useEffect, useMemo, useState } from "react";
import { InputInterface } from ".";
import { IconSearch } from "@tabler/icons-react";
import { DB, ObjectProperty, Record } from "sera-db";
import {
  CloseButton,
  Combobox,
  Divider,
  Group,
  Input,
  Paper,
  Stack,
  Text,
  useCombobox,
} from "@mantine/core";
import { observer } from "mobx-react-lite";

function useSearch(db: DB, property: ObjectProperty) {
  const [query, setQuery] = useState<string>("");
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    db.getByName(property.targetClass)
      .fetch({ limit: 100, offset: 0 })
      .then((resp) => setData(resp.records));
  }, [property.name]);

  const onQueryChange = (query: string) => {
    setQuery(query);
    // TODO: implement an actual search function here!
    const table = db.getByName(property.targetClass);
    setData(
      table.filter((record) =>
        record.name.toLowerCase().includes(query.toLowerCase())
      )
    );
  };

  return {
    data,
    query,
    setQuery: onQueryChange,
    table: db.getByName(property.targetClass),
  };
}

const renderOption = (record: any) => {
  return record.name;
};
const renderRecord = (record: any) => {
  return <Text size="sm">{record.name}</Text>;
};

export const SingleForeignKeyInput = observer(
  <T,>(_props: InputInterface<T>) => {
    return <h1>SingleForeignKey</h1>;
    // const { table, data, query, setQuery } = useSearch(property as ObjectProperty);
    // return <Autocomplete placeholder="Type to search..." data={data} filter={filterFn} />;
  }
);

export const MultiForeignKeyInput = observer(
  <ID extends string | number>({
    db,
    property,
    value: recordIds,
    onChange,
  }: InputInterface<ID[]>) => {
    const { table, data, query, setQuery } = useSearch(
      db,
      property as ObjectProperty
    );

    return (
      <Stack gap="sm">
        <SearchInput
          name={property.name}
          query={query}
          setQuery={setQuery}
          data={data}
          onSelect={(recordId: ID) => {
            if (!recordIds.includes(recordId)) {
              onChange([...recordIds, recordId]);
            }
          }}
          renderOption={renderOption}
          isIdInteger={property.datatype === "integer"}
        />
        <CardList
          items={recordIds.map((id) => table.get(id))}
          onDelete={(delRecord) => {
            onChange(recordIds.filter((item) => item !== delRecord.id));
          }}
          render={renderRecord}
        />
      </Stack>
    );
  }
);

export const SearchInput = <ID extends string | number, R extends Record<ID>>({
  name,
  data,
  onSelect,
  renderOption,
  isIdInteger,
  query,
  setQuery,
}: {
  name?: string;
  query: string;
  setQuery: (query: string) => void;
  onSelect: (id: ID) => void;
  data: R[];
  renderOption: (record: R) => React.ReactNode;
  isIdInteger?: boolean;
}) => {
  // define the combobox store
  const combobox = useCombobox({
    onDropdownClose: () => combobox.resetSelectedOption(),
  });

  // create options for the combobox
  const options = useMemo(() => {
    return data.map((record) => (
      // value has to be a string
      <Combobox.Option value={record.id.toString()} key={record.id}>
        {renderOption(record)}
      </Combobox.Option>
    ));
  }, [data]);

  return (
    <Combobox
      store={combobox}
      onOptionSubmit={(recordId: string) => {
        onSelect((isIdInteger ? parseInt(recordId) : recordId) as ID);
        setQuery("");
        combobox.closeDropdown();
      }}
      offset={0}
      shadow="sm"
    >
      <Combobox.Target>
        <Input
          id={name}
          pointer={true}
          rightSection={<IconSearch size={16} stroke={1.5} />}
          rightSectionPointerEvents="none"
          onClick={() => combobox.toggleDropdown()}
          placeholder="Type to search..."
          value={query}
          onChange={(e) => {
            setQuery(e.currentTarget.value);
          }}
        />
      </Combobox.Target>
      <Combobox.Dropdown>
        <Combobox.Options>
          {options.length === 0 ? (
            <Combobox.Empty>Nothing found</Combobox.Empty>
          ) : (
            options
          )}
        </Combobox.Options>
      </Combobox.Dropdown>
    </Combobox>
  );
};

/// This is a CardList component that is similar to Antd List
export const CardList = <R,>({
  items,
  onDelete,
  render,
}: {
  items: R[];
  onDelete: (value: R) => void;
  render: (value: R) => React.ReactNode;
}) => {
  const els = useMemo(() => {
    const out = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      out.push(
        <Group key={i} justify="space-between" p="sm">
          {render(item)}
          <CloseButton size="sm" onClick={() => onDelete(item)} />
        </Group>
      );
      if (i < items.length - 1) {
        out.push(<Divider key={`divider-${i}`} />);
      }
    }

    return out;
  }, [items]);

  if (els.length === 0) {
    return undefined;
  }
  return <Paper bd={"1px solid #ddd"}>{els}</Paper>;
};
