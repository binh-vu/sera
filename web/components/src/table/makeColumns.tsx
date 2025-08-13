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
export interface SeraColumn<R> {
  /// A unique identifier for the column
  key: string;
  /// The display title of the column, which can include React elements
  title: React.ReactNode;
  /// A function to extract the value for this column from a given record
  accessorFn: (record: R) => any;
  /// A function to render the content of the column for a given record, returning a React node
  render: (record: R) => React.ReactNode;
}

/**
 * Creates a table column configuration for displaying entity properties in a data table.
 *
 * @template R - The type of the record/row data
 * @param db - The database instance used for data operations
 * @param entityRoutes - Configuration object containing routing information for entities
 * @param property - The data object property (DOP) that defines the column's data type and behavior
 * @param nestedKey - Optional string indicating if this is a nested property path
 * @returns A SeraColumn configuration object with key, title, accessor function, and render component
 *
 * @throws {Error} When no display component is found for the specified datatype
 *
 * @example
 * ```tsx
 * const column = makeTableColumn(db, routes, userNameProperty);
 * // Returns a column that displays user names with appropriate formatting
 * ```
 *
 * @remarks
 * The function automatically selects the appropriate display component based on:
 * - Object properties with cardinality "1:N" or "N:N" use MultiForeignKeyDisplay
 * - Object properties with other cardinalities use SingleForeignKeyDisplay
 * - Non-object properties use components from DataType2DisplayComponent mapping
 */
export function makeTableColumn<R>(
  db: DB,
  entityRoutes: EntityRoutes,
  property: DOP,
  {
    title,
    nestedKey,
    component,
  }: {
    title?: React.ReactNode;
    nestedKey?: string;
    component?: React.ComponentType<DisplayInterface<any>>;
  } = {}
): SeraColumn<R> {
  let Component: React.ComponentType<DisplayInterface<any>>;
  if (component !== undefined) {
    Component = component;
  } else if (isObjectProperty(property)) {
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

  const cfg = {
    key: property.name,
    title: title || <MultiLingualString value={property.label} />,
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

  if (nestedKey !== undefined) {
    cfg.accessorFn = (record: any) => {
      return record[nestedKey][property.tsName];
    };
    cfg.render = (record: any) => {
      const value = record[nestedKey][property.tsName];
      return (
        <Component
          db={db}
          property={property}
          value={value}
          entityRoutes={entityRoutes}
        />
      );
    };
  }

  return cfg;
}

export function makeTableColumnFromNestedProperty<R>(
  db: DB,
  entityRoutes: EntityRoutes,
  property: DOP,
  nestedProperty: DOP,
  {
    title,
    nestedKey,
    component,
  }: {
    title?: React.ReactNode;
    nestedKey?: string;
    component?: React.ComponentType<DisplayInterface<any>>;
  } = {}
): SeraColumn<R> {
  let Component: React.ComponentType<DisplayInterface<any>>;
  if (component !== undefined) {
    Component = component;
  } else if (isObjectProperty(nestedProperty)) {
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

  const cfg = {
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

  if (nestedKey !== undefined) {
    cfg.accessorFn = (record: any) => {
      return record[nestedKey][property.tsName][nestedProperty.tsName];
    };
    cfg.render = (record: any) => {
      const value = record[nestedKey][property.tsName][nestedProperty.tsName];
      return (
        <Component
          db={db}
          property={nestedProperty}
          value={value}
          entityRoutes={entityRoutes}
        />
      );
    };
  }

  return cfg;
}

export function makeTableColumns<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>,
  OR
>(
  db: DB,
  schema: Schema<ID, R, DR, PF, F, ST> | EmbeddedSchema<R, DR, PF, F>,
  entityRoutes: EntityRoutes,
  selectedColumns: (PF | SeraColumn<OR>)[],
  options: { nestedKey?: string } = {}
): SeraColumn<OR>[] {
  return selectedColumns.map((columnDef) => {
    if (isSeraColumn(columnDef)) {
      // If it's already a SeraColumn, return it directly
      return columnDef;
    }

    return makeTableColumn(
      db,
      entityRoutes,
      schema.publicProperties[columnDef],
      options
    );
  });
}

export function makeEmbeddedTableColumns<
  R extends GenericEmbeddedRecord<DR>,
  DR extends DraftEmbeddedRecord,
  PF extends keyof R,
  F extends keyof DR,
  OR
>(
  db: DB,
  schema: EmbeddedSchema<R, DR, PF, F>,
  entityRoutes: EntityRoutes,
  selectedColumns: (PF | SeraColumn<OR>)[] = [],
  options: { nestedKey?: string } = {}
): SeraColumn<OR>[] {
  return selectedColumns.map((columnDef) => {
    if (isSeraColumn(columnDef)) {
      // If it's already a SeraColumn, return it directly
      return columnDef;
    }
    return makeTableColumn(
      db,
      entityRoutes,
      schema.publicProperties[columnDef],
      options
    );
  });
}

export function isSeraColumn<R>(
  column: SeraColumn<R> | any
): column is SeraColumn<R> {
  return typeof column === "object" && "key" in column && "title" in column;
}
