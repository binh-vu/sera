/**
 * @file Input component mappings for form fields
 *
 * This module exports interfaces and mappings for form input components.
 * It provides a way to map data types to their corresponding form input components.
 */
import { DataProperty, DataType, DB, ObjectProperty } from "sera-db";
import { BooleanInput } from "./BooleanInput";
import { NumberInput } from "./NumberInput";
import { TextInput } from "./TextInput";
import { DateInput } from "./DateInput";
import { EnumInput } from "./EnumInput";
export { SingleForeignKeyInput, MultiForeignKeyInput } from "./ForeignKeyInput";
export { DateRangeInput, DateTimeRangeInput } from "./DateRangeInput";

/**
 * Interface for input components in forms
 * @interface InputInterface
 * @template T - The type of the input value
 * @property {DataProperty | ObjectProperty} property - The property being edited
 * @property {any} value - The current value of the input
 * @property {function} onChange - Callback function triggered when input value changes
 * @property {boolean | string} [error] - If the type is boolean it will be error, if there is a string message it should display that message
 * @property {boolean} [freeze] - Whether the input is available for editing
 */
export type InputInterface<T> = {
  db: DB;
  property: DataProperty | ObjectProperty;
  value: T;
  onChange: (value: T) => void;
  error?: boolean | string;
  freeze?: boolean;
};

/**
 * Mapping of data types to their corresponding input components
 */
export const DataType2InputComponent: Partial<
  Record<DataType, React.FC<InputInterface<any>>>
> = {
  integer: NumberInput,
  float: NumberInput,
  string: TextInput,
  boolean: BooleanInput,
  "string[]": TextInput,
  enum: EnumInput,
  date: DateInput,
};

export { NumberInput, BooleanInput, TextInput, DateInput, EnumInput };
