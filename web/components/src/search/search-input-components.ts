import { DataType } from "sera-db";
import { NumberInput, InputInterface, TextInput, BooleanInput, DateRangeInput } from "../data";

export const DataType2SearchComponent: Partial<Record<DataType, React.FC<InputInterface<any>>>> = {
  integer: NumberInput,
  float: NumberInput,
  string: TextInput,
  boolean: BooleanInput,
  "string[]": TextInput,
  enum: TextInput,
  date: DateRangeInput,
  datetime: DateRangeInput,
};