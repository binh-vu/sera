import { observer } from "mobx-react-lite";
import {
  DataProperty,
  DraftRecord,
  GenericRecord,
  isDraftRecord,
  isObjectProperty,
  ObjectProperty,
  validators,
  Table,
} from "sera-db";
import { Text, Stack } from "@mantine/core";
import { MultiLingualString } from "../misc";
import { DataType2InputComponent, InputInterface } from "../data";
import {
  MultiForeignKeyInput,
  SingleForeignKeyInput,
} from "../data/inputs/ForeignKeyInput";
import { useState } from "react";

export interface FormNestedPropertyItemProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
> {
  store: Table<ID, R, DR>;

  /// the record being edited
  record: DR | R;

  /// the list of properties being viewed
  properties: (DataProperty | ObjectProperty)[];

  /// The component used to render the field input
  InputComponent: React.ComponentType<InputInterface<any>>;
  onChange?: (newValue: any) => void;
  validator: validators.ValueValidator;
  freeze?: boolean;
}

/**
 * A component that renders a nested property input for forms.
 *
 * This component traverses through a chain of properties to create input fields
 * for deeply nested property values in a record. It handles embedded objects
 * by creating nested form structures.
 *
 * @template ID - The type of the record identifier (string or number)
 * @template R - The type of the generic record extending GenericRecord
 * @template DR - The type of the draft record extending DraftRecord
 *
 * @param props - The component properties
 * @param props.store - The table store containing the record data
 * @param props.record - The draft record being edited
 * @param props.properties - Array of properties defining the path to the nested value
 * @param props.InputComponent - React component used to render the field input
 *
 * @returns A JSX element with input fields for the nested property
 */
export const FormNestedPropertyItem = observer(
  <
    ID extends string | number,
    R extends GenericRecord<ID, DR>,
    DR extends DraftRecord<ID>
  >({
    store,
    record,
    properties,
    InputComponent,
    validator,
    freeze = false,
  }: FormNestedPropertyItemProps<ID, R, DR>) => {
    const prop = properties[properties.length - 1];
    const [error, setError] = useState<string | undefined>(undefined);
    const currentValue = properties.reduce((currentValue, property) => {
      if (currentValue === null || currentValue === undefined) {
        return undefined;
      }
      return currentValue[property.tsName];
    }, record as any);
    const onChange = (currentValue: any) => {
      const findTargetObject = (rootObject: any) => {
        let targetObject = rootObject;
        for (let i = 0; i < properties.length - 1; i++) {
          targetObject = (targetObject as any)[properties[i].tsName];
          //ToDo: Implement the logic to create the embedded object if it's an optional field.
          if (targetObject === undefined) {
            //Change error message, give more information, the property might be wrong
            throw new Error(
              `The current property is undefined, the property name might be incorrect: ${properties[i].tsName}`
            );
          }
          if ((targetObject as any)[prop.updateFuncName] !== undefined) {
            break;
          }
        }
        return targetObject;
      };

      if (isDraftRecord(record)) {
        const targetObject = findTargetObject(record);
        (targetObject as any)[prop.updateFuncName](currentValue);
      } else {
        const draft = record.toDraft();
        const targetObject = findTargetObject(draft);
        (targetObject as any)[prop.updateFuncName](currentValue);
        store.setDraft(draft);
      }

      const validateResult = validator(currentValue);
      if (validateResult.isValid) {
        setError(undefined);
      } else {
        setError(
          validateResult.errorMessage?.t({ args: { name: prop.label } })
        );
      }
    };

    return (
      <Stack gap="xs">
        <Text size="sm" fw={550}>
          <MultiLingualString value={prop.label} />
        </Text>
        <InputComponent
          db={store.db}
          property={prop}
          value={currentValue}
          onChange={onChange}
          error={error}
          freeze={freeze}
        />
      </Stack>
    );
  }
);

export function makeFieldForm<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
>(
  props: (DataProperty | ObjectProperty)[],
  validators: validators.ValueValidator,
  args?: {
    input?: React.ComponentType<InputInterface<any>>;
    freeze?: boolean;
  }
): (store: Table<ID, R, DR>, record: DR) => React.ReactNode {
  const property = props[props.length - 1];
  let inputComponent: React.ComponentType<InputInterface<any>>;

  if (args?.input !== undefined) {
    inputComponent = args.input;
  } else if (isObjectProperty(property)) {
    inputComponent =
      property.cardinality === "N:N" || property.cardinality === "1:N"
        ? MultiForeignKeyInput
        : SingleForeignKeyInput;
  } else {
    if (DataType2InputComponent[property.datatype] === undefined) {
      throw new Error(
        `No input component found for datatype ${property.datatype}`
      );
    }
    inputComponent = DataType2InputComponent[property.datatype]!;
  }
  return (store, record) => {
    return (
      <FormNestedPropertyItem
        store={store}
        record={record}
        properties={props}
        InputComponent={inputComponent}
        validator={validators}
        freeze={args?.freeze ?? false}
      />
    );
  };
}
