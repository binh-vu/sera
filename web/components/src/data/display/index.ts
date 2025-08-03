import { ClassName, DataProperty, DataType, DB, ObjectProperty } from "sera-db";
import { TextDisplay } from "./TextDisplay";
import { NoQueryArgsPathDef } from "sera-route";
export { SingleForeignKeyDisplay, MultiForeignKeyDisplay } from "./ForeignKeyDisplay";

export type EntityRoute = NoQueryArgsPathDef<{ id: "string" | "number" }, any>;
export type EntityRoutes = Record<ClassName, EntityRoute>;

export type DisplayInterface<T> = {
  db: DB;
  property: DataProperty | ObjectProperty;
  nestedProperty?: DataProperty | ObjectProperty;
  value: T;
  // entity routes for foreign key navigation
  entityRoutes: EntityRoutes;
}

export const DataType2DisplayComponent: Partial<Record<DataType, React.ComponentType<DisplayInterface<any>>>> = {
  string: TextDisplay,
  integer: TextDisplay,
  float: TextDisplay,
  boolean: TextDisplay,
  "string[]": TextDisplay,
  enum: TextDisplay,
}