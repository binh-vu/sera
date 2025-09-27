import { Button, Grid, Group, Input, Stack } from "@mantine/core";
import { useMemo, useState } from "react";

import {
  DataProperty,
  DB,
  isObjectProperty,
  MultiLingualString as MLS,
  ObjectProperty,
  QueryConditions,
  QueryOp,
  validators,
} from "sera-db";
import { FormItemHorizontalLayout, FormItemLabel } from "../form";
import { MultiLingualString } from "../misc";
import { InputInterface } from "../data";
import { DataType2SearchComponent } from "./search-input-components";
import {
  MultiForeignKeyInput,
  SingleForeignKeyInput,
} from "../data/inputs/ForeignKeyInput";
import { isEmpty } from "../../../db/src/validators";

export interface SearchFormItemProps<T> {
  db: DB;
  property: DataProperty | ObjectProperty;
  /// The component used to render the input field
  InputComponent?:
    | React.FC<InputInterface<T>>
    | React.ComponentType<InputInterface<T>>;
  /// validator function for the form item
  validator?: validators.ValueValidator;
  layout: FormItemHorizontalLayout;
  /// value and onChange handler are set automatically by the form.
  value: T;
  onChange: (value: T) => void;
}

const UPDATE_BUTTON_TEXT: MLS = {
  lang2value: {
    en: "Update",
    vi: "Cập Nhật",
  },
  lang: "en",
};

const CLEAR_BUTTON_TEXT: MLS = {
  lang2value: {
    en: "Clear",
    vi: "Xóa",
  },
  lang: "en",
};

export const SearchFormItem = ({
  db,
  property,
  InputComponent,
  layout,
  validator,
  value,
  onChange,
}: SearchFormItemProps<any>) => {
  if (InputComponent === undefined) {
    // use default input component
    if (isObjectProperty(property)) {
      if (property.isEmbedded) {
        throw new Error("You should use nested property for embedded object");
      }
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

  const error = useMemo(() => {
    if (validator === undefined) return undefined;
    const res = validator(value);
    return res.errorMessage?.t({ args: { name: property.label } });
  }, [validator, value, property.label]);

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
      {error !== undefined && (
        <Grid gutter="sm">
          <Grid.Col span={layout.labelCol} />
          <Grid.Col span={layout.itemCol}>
            <Input.Error>{error}</Input.Error>
          </Grid.Col>
        </Grid>
      )}
    </Stack>
  );
};

export const SearchForm = ({
  db,
  properties,
  styles,
  className,
  layout,
  onChange,
}: {
  db: DB;
  properties: (Pick<SearchFormItemProps<any>, "property" | "InputComponent"> & {
    // We also need a converter that converts the item value into a query operation
    toQueryOp: (value: any) => QueryOp | undefined;
  })[];
  layout: FormItemHorizontalLayout;
  // styling for the form
  styles?: React.CSSProperties;
  className?: string;
  onChange?: (value: QueryConditions<any>) => void;
}) => {
  const [value, setValue] = useState<any>({});

  const [searchItems, toQueryOps] = useMemo(() => {
    const output = [];
    const toQueryOps: { [key: string]: (value: any) => QueryOp | undefined } =
      {};

    for (const prop of properties) {
      let validator = undefined;
      let toQueryOp: (value: any) => QueryOp | undefined = (val: any) => {
        if (isEmpty(val)) return undefined;
        return { op: "eq", value: val };
      };

      if (
        prop.property.datatype === "date" ||
        prop.property.datatype === "datetime"
      ) {
        // Date & DateTime search will have a validator that validate the start time is before the end time
        validator = validators.validateTimeRange;
        toQueryOp = (val: { start?: Date; end?: Date }) => {
          if (val.start !== undefined && val.end !== undefined) {
            return {
              op: "bti",
              value: [val.start.getTime(), val.end.getTime()],
            };
          } else if (val.start !== undefined) {
            return { op: "gte", value: val.start.getTime() };
          } else if (val.end !== undefined) {
            return { op: "lte", value: val.end.getTime() };
          } else {
            return undefined;
          }
        };
      }

      toQueryOps[prop.property.tsName] = toQueryOp;

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
          validator={validator}
        />
      );
    }
    return [output, toQueryOps];
  }, [properties, value, setValue]);

  const updateSearchForm = (value: any) => {
    const conditions: QueryConditions<any> = {};
    for (const prop of properties) {
      conditions[prop.property.tsName] = toQueryOps[prop.property.tsName](
        value[prop.property.tsName]
      );
    }
    onChange?.(conditions);
  };

  return (
    <Stack gap="sm" className={className} style={styles}>
      {searchItems}
      <Group gap="sm" justify="flex-end">
        <Button
          variant="light"
          size="xs"
          color="gray"
          onClick={() => {
            setValue({});
            updateSearchForm({});
          }}
        >
          <MultiLingualString value={CLEAR_BUTTON_TEXT} />
        </Button>
        <Button
          variant="light"
          size="xs"
          onClick={() => updateSearchForm(value)}
        >
          <MultiLingualString value={UPDATE_BUTTON_TEXT} />
        </Button>
      </Group>
    </Stack>
  );
};
