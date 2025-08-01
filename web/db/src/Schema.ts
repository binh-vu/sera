import { ValueNormalizer } from "./normalizers";
import { Record as DBRecord, DraftEmbeddedRecord, DraftRecord } from "./Record";
import { ValueValidator } from "./validators";
export type PropertyName = string;
export type TargetClassName = string;
export type DataType = "string" | "integer" | "float" | "boolean" | "date" | "datetime" | "string[]" | "enum" | "dict";
export type Enum = { [key: string]: string | number };

export interface MultiLingualString {
  lang2value: { [lang: string]: string };
  // default language -- only used when the chosen language is not available
  lang: string;
}

// We do not use enum here because Constraint can have arguments
export type Constraint =
  | "phone_number"
  | "email"
  | "not_empty"
  | "url"
  | "username"
  | "password"
  | "positive_number";

export interface Property {
  // name of the property
  name: PropertyName;
  // name of the property in TypeScript
  tsName: PropertyName;
  // name of the function to update the property
  updateFuncName: PropertyName;
  // label of the property
  label: MultiLingualString;
  // description of the property
  description?: MultiLingualString;
  // whether the property is required
  isRequired: boolean;
  // list of constraints applied to the property
  constraints: Constraint[];
}

export interface ObjectProperty extends Property {
  // name of the target class
  targetClass: TargetClassName;
  // the cardinality of the property -- is it one-to-one, many-to-one, etc.
  cardinality: "1:1" | "1:N" | "N:1" | "N:N";
  // data type of the id property of the target class if not embedded
  // if embedded, it will be undefined
  datatype?: DataType;
  // whether the whole object is embedded in the parent object
  // if false, only the id of the object is stored in the parent object
  isEmbedded: boolean;
}

export interface DataProperty extends Property {
  // data type of the property
  datatype: DataType;
  // if the property is an enum, this will contain the enum class
  enumType?: Enum;
}

type NoStale<T> = T extends { stale: boolean } ? never : T;
export type GenericRecord<ID, DR> = DBRecord<ID> & {
  toDraft(): DR;
};

export type SchemaType<
  ID,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR
> = {
  id: ID;
  // ensure that cls has toDraft & no stale property for isDraftRecord check
  cls: R & NoStale<R>;
  // draftCls has stale property
  draftCls: DR;
  publicProperties: PF;
  allProperties: F;
};

export interface Schema<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  publicProperties: Record<
    ST["publicProperties"],
    DataProperty | ObjectProperty
  >;
  allProperties: Record<ST["allProperties"], DataProperty | ObjectProperty>;
  validators: Record<ST["allProperties"], ValueValidator>;
  normalizers: Partial<Record<ST["allProperties"], ValueNormalizer<any>>>;
  primaryKey: ST["publicProperties"] & ST["allProperties"];
}

export type GenericEmbeddedRecord<DR> = {
  toDraft(): DR;
};

export interface EmbeddedSchema<
  R extends GenericEmbeddedRecord<DR>,
  DR extends DraftEmbeddedRecord,
  PF extends keyof R,
  F extends keyof DR,
> {
  publicProperties: Record<
    PF,
    DataProperty | ObjectProperty
  >;
  allProperties: Record<F, DataProperty | ObjectProperty>;
  validators: Record<F, ValueValidator>;
  normalizers: Partial<Record<F, ValueNormalizer<any>>>;
}

/**
 * Type guard function to check if a value is a DraftRecord.
 *
 * @param record
 * @returns
 */
export function isDraftRecord<
  ID,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
>(record: R | DR): record is DR {
  return (record as any)["stale"] !== undefined;
}

/**
 * Type guard function to check if a value is a MultiLingualString.
 * 
 * @param value - The value to check
 * @returns True if the value is a MultiLingualString, false otherwise
 * 
 * @example
 * const value = { lang: 'en', lang2value: { en: 'Hello', fr: 'Bonjour' } };
 * if (isMultiLingualString(value)) {
 *   // value is now typed as MultiLingualString
 *   console.log(value.lang2value.en);
 * }
 */
export function isMultiLingualString(value: unknown): value is MultiLingualString {
  return (
    typeof value === 'object' &&
    value !== null &&
    'lang' in value &&
    'lang2value' in value
    //  &&
    // typeof (value as MultiLingualString).lang === 'string' &&
    // typeof (value as MultiLingualString).lang2value === 'object' &&
    // (value as MultiLingualString).lang2value !== null
  );
}

/**
 * Determines if the given property is an `ObjectProperty`.
 *
 * This function performs a type guard check to determine if the provided
 * `property` is of type `ObjectProperty` by verifying the presence of the
 * `targetClass` property.
 *
 * @param property - The property to check, which can be either a `DataProperty` or an `ObjectProperty`.
 * @returns A boolean indicating whether the property is an `ObjectProperty`.
 */
export function isObjectProperty(
  property: DataProperty | ObjectProperty
): property is ObjectProperty {
  return (property as ObjectProperty).targetClass !== undefined;
}