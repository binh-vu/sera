import { Button, Grid, Group, Input, Stack } from "@mantine/core";
import { useEffect, useMemo, useState } from "react";

import {
  DataProperty,
  DB,
  I18NStore,
  isObjectProperty,
  MultiLingualString as MLS,
  ObjectProperty,
  QueryConditions,
  QueryOp,
  validators,
} from "sera-db";
import { FormItemHorizontalLayout, FormItemLabel } from "../form";
import { MultiLingualString, translateMultiLingualString } from "../misc";
import { InputInterface } from "../data";
import { DataType2SearchComponent } from "./search-input-components";
import {
  MultiForeignKeyInput,
  SingleForeignKeyInput,
} from "../data/inputs/ForeignKeyInput";
import { isEmpty } from "../../../db/src/validators";
import { formatDate, formatDateTime } from "../data/display/DateTimeDisplay";
import dayjs from "dayjs";

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

export interface SearchFormProps {
  db: DB;
  properties: {
    property: DataProperty | ObjectProperty;
    /// The component used to render the input field
    InputComponent?:
      | React.FC<InputInterface<any>>
      | React.ComponentType<InputInterface<any>>;
    // We also need a converter that converts the item value into a query operation
    toQueryOp?: (value: any) => QueryOp | undefined;
  }[];
  layout: FormItemHorizontalLayout;
  // styling for the form
  styles?: React.CSSProperties;
  className?: string;
  onChange: (value: QueryConditions<any>) => void;
  queryConditions: QueryConditions<any>;
}

/// Get the number of active filters from the query conditions
export function getNumberOfFilters({
  properties,
  queryConditions,
}: {
  properties: SearchFormProps["properties"];
  queryConditions: QueryConditions<any>;
}) {
  return properties.reduce((count, prop) => {
    const condition = queryConditions[prop.property.tsName];
    if (condition === undefined) return count;
    return count + 1;
  }, 0);
}

const formatDateTimeWithoutSeconds = (locale: Intl.Locale, value: Date) =>
  formatDateTime(locale, value, false);

export function getReadableFilters({
  properties,
  queryConditions,
}: {
  properties: SearchFormProps["properties"];
  queryConditions: QueryConditions<any>;
}): string {
  const locale = I18NStore.getInstance().getLocale();

  const parts: string[] = [];
  for (const prop of properties) {
    const condition = queryConditions[prop.property.tsName];
    if (condition === undefined) continue;

    if (parts.length > 0) {
      parts.push(" & ");
    }

    if (
      prop.property.datatype === "date" ||
      prop.property.datatype === "datetime"
    ) {
      const formatFn =
        prop.property.datatype === "date"
          ? formatDate
          : formatDateTimeWithoutSeconds;

      if (condition.op === "bti") {
        parts.push(formatFn(locale, dayjs(condition.value[0]).toDate()));
        parts.push(" ≤ ");
        parts.push(translateMultiLingualString(locale, prop.property.label));
        parts.push(" ≤ ");
        parts.push(formatFn(locale, dayjs(condition.value[1]).toDate()));
      } else if (condition.op === "gte") {
        parts.push(translateMultiLingualString(locale, prop.property.label));
        parts.push(" ≥ ");
        parts.push(formatFn(locale, dayjs(condition.value).toDate()));
      } else if (condition.op === "lte") {
        parts.push(translateMultiLingualString(locale, prop.property.label));
        parts.push(" ≤ ");
        parts.push(formatFn(locale, dayjs(condition.value).toDate()));
      }
    } else {
      parts.push(translateMultiLingualString(locale, prop.property.label));
      if (condition.op === "eq") {
        parts.push(" = ");
      } else {
        parts.push(` ${condition.op} `);
      }

      parts.push(condition.value.toString());
    }
  }

  return parts.join("");
}

export const SearchForm = ({
  db,
  properties,
  styles,
  className,
  layout,
  onChange,
  queryConditions,
}: SearchFormProps) => {
  const [value, setValue] = useState<any>({});

  useEffect(() => {
    const newvalue: any = {};
    for (const prop of properties) {
      const condition = queryConditions[prop.property.tsName];
      if (condition === undefined) continue;

      if (
        prop.property.datatype === "date" ||
        prop.property.datatype === "datetime"
      ) {
        if (condition.op === "bti") {
          newvalue[prop.property.tsName] = {
            start: condition.value[0]
              ? new Date(condition.value[0])
              : undefined,
            end: condition.value[1] ? new Date(condition.value[1]) : undefined,
          };
        } else if (condition.op === "gte") {
          newvalue[prop.property.tsName] = {
            start: condition.value ? new Date(condition.value) : undefined,
            end: undefined,
          };
        } else if (condition.op === "lte") {
          newvalue[prop.property.tsName] = {
            start: undefined,
            end: condition.value ? new Date(condition.value) : undefined,
          };
        }
      } else {
        newvalue[prop.property.tsName] = condition.value;
      }
    }

    setValue(newvalue);
  }, [properties, queryConditions]);

  const [searchItems, toQueryOps, valueValidators] = useMemo(() => {
    const output = [];
    const toQueryOps: { [key: string]: (value: any) => QueryOp | undefined } =
      {};
    const valueValidators: {
      [key: string]: validators.ValueValidator | undefined;
    } = {};

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
              value: [val.start.toISOString(), val.end.toISOString()],
            };
          } else if (val.start !== undefined) {
            return { op: "gte", value: val.start.toISOString() };
          } else if (val.end !== undefined) {
            return { op: "lte", value: val.end.toISOString() };
          } else {
            return undefined;
          }
        };
      }

      toQueryOps[prop.property.tsName] = toQueryOp;
      valueValidators[prop.property.tsName] = validator;

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

    return [output, toQueryOps, valueValidators];
  }, [properties, value, setValue]);

  const updateSearchForm = (value: Record<string, any>) => {
    const conditions: QueryConditions<any> = {};
    for (const prop of properties) {
      if (value[prop.property.tsName] === undefined) continue;
      const con = toQueryOps[prop.property.tsName](value[prop.property.tsName]);
      if (con !== undefined) {
        conditions[prop.property.tsName] = con;
      }
    }
    onChange(conditions);
  };

  const isValueValid = useMemo(() => {
    return (value: Record<string, any>) => {
      for (const prop of properties) {
        const validator = valueValidators[prop.property.tsName];
        if (
          validator !== undefined &&
          !validator(value[prop.property.tsName]).isValid
        ) {
          return false;
        }
      }
      return true;
    };
  }, [properties, valueValidators]);

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
          disabled={Object.keys(value).length === 0}
        >
          <MultiLingualString value={CLEAR_BUTTON_TEXT} />
        </Button>
        <Button
          variant="light"
          size="xs"
          onClick={() => updateSearchForm(value)}
          disabled={!isValueValid(value)}
        >
          <MultiLingualString value={UPDATE_BUTTON_TEXT} />
        </Button>
      </Group>
    </Stack>
  );
};
