import { Record as DBRecord, DraftRecord } from "./Record";
export type PropertyName = string;
export type TargetClassName = string;
export type DataType = "string" | "number" | "boolean" | "string | undefined";

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
  | "password";

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
  // whether the property is a list of values
  isList: boolean;
  // whether the property is required
  isRequired: boolean;
  // list of constraints applied to the property
  constraints: Constraint[];
}

export interface ObjectProperty extends Property {
  // name of the target class
  targetClass: TargetClassName;
  // data type of the id property of the target class if not embedded
  datatype: DataType;
  // whether the whole object is embedded in the parent object
  // if false, only the id of the object is stored in the parent object
  isEmbedded: boolean;
}

export interface DataProperty extends Property {
  // data type of the property
  datatype: DataType;
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
  ID,
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
  primaryKey?: keyof ST["cls"];
}

export function isDraftRecord<
  ID,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
>(record: R | DR): record is DR {
  return (record as any)["stale"] !== undefined;
}
