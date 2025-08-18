import { ClassName, DataProperty, DataType, DB, ObjectProperty } from "sera-db";
import { TextDisplay } from "./TextDisplay";
import { NoQueryArgsPathDef } from "sera-route";
import { DateDisplay, DateTimeDisplay, DateTimeHideTimeDisplay } from "./DateTimeDisplay";
import { BooleanDisplay } from "./BooleanDisplay";
import { EnumDisplay } from "./EnumDisplay";
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
  boolean: BooleanDisplay,
  "string[]": TextDisplay,
  enum: EnumDisplay,
  datetime: DateTimeDisplay,
  date: DateDisplay
}

export {
  DateDisplay,
  DateTimeDisplay,
  DateTimeHideTimeDisplay
}