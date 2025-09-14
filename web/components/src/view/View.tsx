import { useMemo } from "react";
import {
  DataProperty,
  DraftRecord,
  GenericRecord,
  isObjectProperty,
  ObjectProperty,
  Schema,
  SchemaType,
  Table,
} from "sera-db";
import { Grid, Stack } from "@mantine/core";
import {
  DataType2DisplayComponent,
  DisplayInterface,
  MultiForeignKeyDisplay,
  SingleForeignKeyDisplay,
} from "../data/display";
import { ViewItem } from "./ViewItem";
import { ViewNestedPropertyItem } from "./ViewNestedPropertyItem";

const SPAN_COL = 12;

/// Group of fields that are grouped together in the view
export interface FieldGroup<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  name?: string;
  fields: (
    | ST["allProperties"]
    | {
        prop: ST["allProperties"];
        display: React.ComponentType<DisplayInterface<any>>;
      }
    | ((store: Table<ID, R, DR>, record: R) => React.ReactNode)
  )[][];
}

export interface SeraViewProps<
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
  store: Table<ID, R, DR>;

  // layout of the fields
  fieldGroups: FieldGroup<ID, R, DR, PF, F, ST>[];

  // the record being viewed
  record: R;

  // styling for the form
  styles?: React.CSSProperties;
  className?: string;
}

export const SeraView = <
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  props: SeraViewProps<ID, R, DR, PF, F, ST>
) => {
  const schema = props.schema;

  const viewItems = useMemo(() => {
    return props.fieldGroups.map((group, index) => {
      return makeFieldGroup(schema, props.store, props.record, index, group);
    });
  }, [schema, props.store, props.record, props.fieldGroups]);

  return (
    <Stack gap="sm" className={props.className} style={props.styles}>
      {viewItems}
    </Stack>
  );
};

function makeFieldGroup<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  schema: Schema<ID, R, DR, PF, F, ST>,
  store: Table<ID, R, DR>,
  record: R,
  key: string | number,
  group: FieldGroup<ID, R, DR, PF, F, ST>
) {
  const fields = group.fields;
  const cols = [];

  for (let i = 0; i < fields.length; i++) {
    const span = SPAN_COL / fields[i].length;
    if (!Number.isInteger(span)) {
      throw new Error(`Span must be an integer, but got ${span} for row ${i}`);
    }

    for (let j = 0; j < fields[i].length; j++) {
      const field = fields[i][j];
      let fieldElement: React.ReactNode;

      if (typeof field === "function") {
        fieldElement = field(store, record);
      } else if (typeof field === "object" && "prop" in field) {
        const prop = schema.allProperties[field.prop];
        const displayComponent = field.display;
        fieldElement = (
          <ViewItem
            store={store}
            record={record}
            property={prop}
            DisplayComponent={displayComponent}
          />
        );
      } else {
        const prop = schema.allProperties[field];

        let displayComponent: React.ComponentType<DisplayInterface<any>>;
        if (isObjectProperty(prop)) {
          displayComponent =
            prop.cardinality === "N:N" || prop.cardinality === "1:N"
              ? MultiForeignKeyDisplay
              : SingleForeignKeyDisplay;
        } else {
          if (DataType2DisplayComponent[prop.datatype] === undefined) {
            throw new Error(
              `No display component found for datatype ${prop.datatype}`
            );
          }
          displayComponent = DataType2DisplayComponent[prop.datatype]!;
        }

        fieldElement = (
          <ViewItem
            store={store}
            record={record}
            property={prop}
            DisplayComponent={displayComponent}
          />
        );
      }

      cols.push(
        <Grid.Col key={`${i}-${j}`} span={span}>
          {fieldElement}
        </Grid.Col>
      );
    }
  }

  return (
    <Grid key={key} gutter="sm">
      {cols}
    </Grid>
  );
}

export function makeFieldDisplay<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
>(
  props: (DataProperty | ObjectProperty)[],
  display?: React.ComponentType<DisplayInterface<any>>
): (store: Table<ID, R, DR>, record: R) => React.ReactNode {
  const property = props[props.length - 1];
  let displayComponent: React.ComponentType<DisplayInterface<any>>;
  if (display !== undefined) {
    displayComponent = display;
  } else if (isObjectProperty(property)) {
    displayComponent =
      property.cardinality === "N:N" || property.cardinality === "1:N"
        ? MultiForeignKeyDisplay
        : SingleForeignKeyDisplay;
  } else {
    if (DataType2DisplayComponent[property.datatype] === undefined) {
      throw new Error(
        `No display component found for datatype ${property.datatype}`
      );
    }
    displayComponent = DataType2DisplayComponent[property.datatype]!;
  }

  return (store, record) => {
    return (
      <ViewNestedPropertyItem
        store={store}
        record={record}
        properties={props}
        DisplayComponent={displayComponent}
      />
    );
  };
}
