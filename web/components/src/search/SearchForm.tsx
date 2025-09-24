import { Button, Grid, Group, Stack } from "@mantine/core";
import { useMemo, useState } from "react";

import {
  DataProperty,
  DB,
  isObjectProperty,
  MultiLingualString as MLS,
  ObjectProperty,
} from "sera-db";
import { FormItemHorizontalLayout, FormItemLabel } from "../form";
import { MultiLingualString } from "../misc";
import { InputInterface } from "../data";
import { DataType2SearchComponent } from "./search-input-components";
import {
  MultiForeignKeyInput,
  SingleForeignKeyInput,
} from "../data/inputs/ForeignKeyInput";

export interface SearchFormItemProps {
  db: DB;
  property: DataProperty | ObjectProperty;
  /// The component used to render the input field
  InputComponent?:
    | React.FC<InputInterface<any>>
    | React.ComponentType<InputInterface<any>>;
  layout: FormItemHorizontalLayout;
  value: any;
  onChange: (value: any) => void;
}

export const SearchFormItem = ({
  db,
  property,
  InputComponent,
  layout,
  value,
  onChange,
}: SearchFormItemProps) => {
  if (InputComponent === undefined) {
    // use default input component
    if (isObjectProperty(property)) {
      InputComponent =
        property.cardinality === "N:N" || property.cardinality === "1:N"
          ? MultiForeignKeyInput
          : SingleForeignKeyInput;
    } else {
      if (DataType2SearchComponent[property.datatype] === undefined) {
        throw new Error(
          `No input component found for datatype ${property.datatype}`
        );
      }
      InputComponent = DataType2SearchComponent[property.datatype]!;
    }
  }

  return (
    <Stack gap={5}>
      <Grid gutter="sm">
        <Grid.Col
          span={layout.labelCol}
          style={{
            display: "flex",
            justifyContent: layout.align || "left",
          }}
        >
          <FormItemLabel
            label={<MultiLingualString value={property.label} />}
            name={property.name}
            required={property.isRequired}
            tooltip={
              property.description !== undefined ? (
                <MultiLingualString value={property.description} />
              ) : undefined
            }
            align={layout.align}
          />
        </Grid.Col>
        <Grid.Col span={layout.itemCol}>
          <InputComponent
            db={db}
            property={property}
            value={value}
            onChange={onChange}
          />
        </Grid.Col>
      </Grid>
    </Stack>
  );
};

export const SearchForm = ({
  db,
  properties,
  styles,
  className,
  layout,
}: {
  db: DB;
  properties: Pick<SearchFormItemProps, "property" | "InputComponent">[];
  layout: FormItemHorizontalLayout;
  // styling for the form
  styles?: React.CSSProperties;
  className?: string;
}) => {
  const [value, setValue] = useState<any>({});

  const searchItems = useMemo(() => {
    const output = [];
    for (const prop of properties) {
      output.push(
        <SearchFormItem
          key={prop.property.name}
          db={db}
          property={prop.property}
          InputComponent={prop.InputComponent}
          value={value[prop.property.tsName]}
          onChange={(val: any) => {
            setValue({ ...value, [prop.property.tsName]: val });
          }}
          layout={layout}
        />
      );
    }
    return output;
  }, [properties, value, setValue]);

  return (
    <Stack gap="sm" className={className} style={styles}>
      {searchItems}
      <Group gap="sm" justify="flex-end">
        <Button variant="light" size="xs" color="gray">
          Clear
        </Button>
        <Button variant="light" size="xs">
          Update
        </Button>
      </Group>
    </Stack>
  );
};
