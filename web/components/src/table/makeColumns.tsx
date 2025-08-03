import {
  DataProperty,
  DB,
  DraftEmbeddedRecord,
  DraftRecord,
  EmbeddedSchema,
  GenericEmbeddedRecord,
  GenericRecord,
  isObjectProperty,
  ObjectProperty,
  Schema,
  SchemaType,
} from "sera-db";
import { MultiLingualString } from "../basic";
import {
  DataType2DisplayComponent,
  DisplayInterface,
  EntityRoutes,
  MultiForeignKeyDisplay,
  SingleForeignKeyDisplay,
} from "../data/display";

type DOP = DataProperty | ObjectProperty;

/**
 * Represents a column configuration for a table component.
 */
export interface SeraColumn {
  /// A unique identifier for the column
  key: string;
  /// The display title of the column, which can include React elements
  title: React.ReactNode;
  /// A function to extract the value for this column from a given record
  accessorFn: (record: any) => any;
  /// A function to render the content of the column for a given record, returning a React node
  render: (record: any) => React.ReactNode;
}

export function makeTableColumn(
  db: DB,
  entityRoutes: EntityRoutes,
  property: DOP
): SeraColumn {
  let Component: React.ComponentType<DisplayInterface<any>>;
  if (isObjectProperty(property)) {
    if (property.cardinality === "1:N" || property.cardinality === "N:N") {
      Component = MultiForeignKeyDisplay;
    } else {
      Component = SingleForeignKeyDisplay;
    }
  } else {
    if (DataType2DisplayComponent[property.datatype] === undefined) {
      throw new Error(
        `No display component found for datatype ${property.datatype}`
      );
    }
    Component = DataType2DisplayComponent[property.datatype]!;
  }

  return {
    key: property.name,
    title: <MultiLingualString value={property.label} />,
    accessorFn: (record: any) => {
      return record[property.tsName];
    },
    render: (record: any) => {
      const value = record[property.tsName];
      return (
        <Component
          db={db}
          property={property}
          value={value}
          entityRoutes={entityRoutes}
        />
      );
    },
  };
}

export function makeTableColumnFromNestedProperty(
  db: DB,
  entityRoutes: EntityRoutes,
  property: DOP,
  nestedProperty: DOP,
  { title }: { title?: React.ReactNode } = {}
): SeraColumn {
  let Component: React.ComponentType<DisplayInterface<any>>;
  if (isObjectProperty(nestedProperty)) {
    if (
      nestedProperty.cardinality === "1:N" ||
      nestedProperty.cardinality === "N:N"
    ) {
      Component = MultiForeignKeyDisplay;
    } else {
      Component = SingleForeignKeyDisplay;
    }
  } else {
    if (DataType2DisplayComponent[nestedProperty.datatype] === undefined) {
      throw new Error(
        `No display component found for datatype ${nestedProperty.datatype}`
      );
    }
    Component = DataType2DisplayComponent[nestedProperty.datatype]!;
  }

  return {
    key: property + "." + nestedProperty.name,
    title: title || <MultiLingualString value={nestedProperty.label} />,
    accessorFn: (record: any) => {
      return record[property.tsName][nestedProperty.tsName];
    },
    render: (record: any) => {
      const value = record[property.tsName][nestedProperty.tsName];
      return (
        <Component
          db={db}
          property={nestedProperty}
          value={value}
          entityRoutes={entityRoutes}
        />
      );
    },
  };
}

export function makeTableColumns<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  db: DB,
  schema: Schema<ID, R, DR, PF, F, ST> | EmbeddedSchema<R, DR, PF, F>,
  entityRoutes: EntityRoutes,
  selectedColumns: (PF | SeraColumn)[]
): SeraColumn[] {
  return selectedColumns.map((columnDef) => {
    if (isSeraColumn(columnDef)) {
      // If it's already a SeraColumn, return it directly
      return columnDef;
    }
    return makeTableColumn(
      db,
      entityRoutes,
      schema.publicProperties[columnDef]
    );
  });
}

export function makeEmbeddedTableColumns<
  R extends GenericEmbeddedRecord<DR>,
  DR extends DraftEmbeddedRecord,
  PF extends keyof R,
  F extends keyof DR
>(
  db: DB,
  schema: EmbeddedSchema<R, DR, PF, F>,
  entityRoutes: EntityRoutes,
  selectedColumns: (PF | SeraColumn)[]
): SeraColumn[] {
  return selectedColumns.map((columnDef) => {
    if (isSeraColumn(columnDef)) {
      // If it's already a SeraColumn, return it directly
      return columnDef;
    }
    return makeTableColumn(
      db,
      entityRoutes,
      schema.publicProperties[columnDef]
    );
  });
}

export function isSeraColumn(column: SeraColumn | any): column is SeraColumn {
  return typeof column === "object" && "key" in column && "title" in column;
}
