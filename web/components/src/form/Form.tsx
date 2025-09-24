import { useMemo } from "react";
import {
  DraftRecord,
  GenericRecord,
  isDraftRecord,
  isObjectProperty,
  MultiLingualString,
  Schema,
  SchemaType,
  Table,
} from "sera-db";
import { Button, Fieldset, Grid, Group, Stack } from "@mantine/core";
import { DataType2InputComponent, InputInterface } from "../data/inputs";
import {
  MultiForeignKeyInput,
  SingleForeignKeyInput,
} from "../data/inputs/ForeignKeyInput";
import { FormItem, FormItemLayout } from "./FormItem";

const SPAN_COL = 12;

/// A custom field that users can define in the form.
export interface CustomField {
  name: string;
  label: MultiLingualString;
  description?: MultiLingualString;
}

/// Group of fields that are grouped together in the form
export interface FieldGroup<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  name?: string;
  fields: ST["allProperties"][][];
}

export interface SeraFormProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  // record schema
  schema: Schema<ID, R, DR, PF, F, ST>;
  // the store that contains records
  store: Table<ST["id"], ST["cls"], ST["draftCls"]>;

  // layout of the form items
  fieldGroups: FieldGroup<ID, R, DR, PF, F, ST>[];
  layout?: FormItemLayout;

  // actions to be displayed at the bottom of the form
  actions: {
    variant: "filled" | "light" | "outline";
    label?: React.ReactNode;
    disabled?: boolean;
    onClick?: () => void;
  }[];

  // the record being edited
  record: ST["cls"] | ST["draftCls"];

  // styling for the form
  styles?: React.CSSProperties;
  className?: string;

  // function to be called when the form is submitted
  // this is useful when you really want to enable submit the form by pressing enter
  // in any input field (recommended by WCAG). However, a user may make a mistake and press enter
  // when they are not ready to submit the form. So, this is not recommended.
  onSubmit?: (record: ST["draftCls"]) => void;
}

/**
 * A form component that renders form items based on a schema from sera-db.
 *
 * This component provides a structured way to render form fields based on a schema definition,
 * with support for grouping fields, custom layouts, and form actions.
 *
 * @template ID - The type of ID used for records
 * @template R - The record type that extends GenericRecord
 * @template DR - The draft record type that extends DraftRecord
 * @template PF - The type of public fields in R
 * @template F - The type of fields in DR
 * @template ST - The schema type that extends SchemaType
 *
 * @example
 * ```tsx
 * <SeraForm
 *   schema={userSchema}
 *   store={userStore}
 *   fieldGroups={[
 *     {
 *       name: "Basic Info",
 *       fields: [["firstName", "lastName"], ["email"]]
 *     }
 *   ]}
 *   layout={{ type: "horizontal", labelCol: 3, itemCol: 9 }}
 *   actions={[
 *     { variant: "filled", label: "Save", onClick: handleSave },
 *     { variant: "outline", label: "Cancel", onClick: handleCancel }
 *   ]}
 *   record={userRecord}
 * />
 * ```
 */
export const SeraForm = <
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  props: SeraFormProps<ID, R, DR, PF, F, ST>
) => {
  const schema = props.schema;

  const formItems = useMemo(() => {
    const maxNumColumns = Math.max(
      ...props.fieldGroups.map((group) => {
        return Math.max(...group.fields.map((fields) => fields.length));
      })
    );
    return props.fieldGroups.map((group, index) => {
      return makeFieldGroup(
        schema,
        props.store,
        props.record,
        index,
        group,
        maxNumColumns,
        props.layout
      );
    });
  }, [schema, props.store, props.record, props.fieldGroups, props.layout]);

  return (
    <form
      onSubmit={
        props.onSubmit === undefined
          ? undefined
          : (e) => {
              e.preventDefault();
              if (props.onSubmit !== undefined && isDraftRecord(props.record)) {
                props.onSubmit(props.record);
              }
            }
      }
    >
      <Stack gap="sm" className={props.className} style={props.styles}>
        {formItems}
        <Group gap="sm">
          {props.actions.map((action, index) => {
            return (
              <Button
                key={index}
                variant={action.variant}
                onClick={() => {
                  if (action.onClick !== undefined) {
                    action.onClick();
                  }
                }}
                disabled={action.disabled}
              >
                {action.label}
              </Button>
            );
          })}
        </Group>
      </Stack>
    </form>
  );
};

/**
 * Creates a field group for the form based on the provided schema and layout configuration.
 *
 * This function generates the appropriate Grid and FormItem components for each field in the group,
 * handling layout calculations and component rendering.
 *
 * @template ID - The type of ID used for records
 * @template R - The record type that extends GenericRecord
 * @template DR - The draft record type that extends DraftRecord
 * @template PF - The type of public fields in R
 * @template F - The type of fields in DR
 * @template ST - The schema type that extends SchemaType
 *
 * @param schema - The schema definition containing property information
 * @param store - The table store that contains the records
 * @param record - The record being edited (either a full record or draft)
 * @param key - A unique key identifier for the field group
 * @param group - The field group configuration defining fields and optional name
 * @param maxNumColumns - The maximum number of columns across all field groups
 * @param layout - Optional layout configuration for form items
 * @returns A React element representing the field group with appropriate layout and styling
 * @throws Error if the calculated span is not an integer
 */
function makeFieldGroup<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  schema: Schema<ID, R, DR, PF, F, ST>,
  store: Table<ST["id"], ST["cls"], ST["draftCls"]>,
  record: ST["cls"] | ST["draftCls"],
  key: string | number,
  group: FieldGroup<ID, R, DR, PF, F, ST>,
  maxNumColumns: number,
  layout?: FormItemLayout
) {
  const fields = group.fields;
  const cols = [];

  for (let i = 0; i < fields.length; i++) {
    const span = SPAN_COL / fields[i].length;
    if (!Number.isInteger(span)) {
      throw new Error(`Span must be an integer, but got ${span} for row ${i}`);
    }

    // update the labelCol and itemCol based on the maximum number of columns
    let updatedLayout;
    if (
      layout !== undefined &&
      typeof layout === "object" &&
      layout.type === "horizontal"
    ) {
      updatedLayout = {
        ...layout,
        // the size of labelCol must match the minimum size of labelCol across different groups
        // and rows -- if the result isn't a whole number, we may see unaligned labels
        // but this is okay as users will need to adjust the layout anyway.
        labelCol: Math.floor(
          (layout.labelCol * fields[i].length) / maxNumColumns
        ),
        itemCol:
          SPAN_COL -
          Math.floor((layout.labelCol * fields[i].length) / maxNumColumns),
      };
    } else {
      updatedLayout = layout;
    }

    for (let j = 0; j < fields[i].length; j++) {
      const field = fields[i][j];
      const prop = schema.allProperties[field];

      let inputComponent: React.ComponentType<InputInterface<any>>;
      if (isObjectProperty(prop)) {
        inputComponent =
          prop.cardinality === "N:N" || prop.cardinality === "1:N"
            ? MultiForeignKeyInput
            : SingleForeignKeyInput;
      } else {
        if (DataType2InputComponent[prop.datatype] === undefined) {
          throw new Error(
            `No input component found for datatype ${prop.datatype}`
          );
        }
        inputComponent = DataType2InputComponent[prop.datatype]!;
      }

      cols.push(
        <Grid.Col key={`${i}-${j}`} span={span}>
          <FormItem
            store={store}
            record={record}
            property={prop}
            layout={updatedLayout}
            InputComponent={inputComponent}
            validator={schema.validators[field]}
          />
        </Grid.Col>
      );
    }
  }

  const content = (
    <Grid key={key} gutter="sm">
      {cols}
    </Grid>
  );

  if (group.name !== undefined) {
    return (
      <Fieldset key={key} legend={group.name}>
        {content}
      </Fieldset>
    );
  }

  return content;
}
