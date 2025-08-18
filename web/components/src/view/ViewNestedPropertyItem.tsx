import { observer } from "mobx-react-lite";
import {
  DataProperty,
  DraftRecord,
  GenericRecord,
  ObjectProperty,
  Table,
} from "sera-db";
import { Text } from "@mantine/core";
import { MultiLingualString } from "../basic";
import { DisplayInterface, EntityRoutes } from "../data";

export interface ViewNestedPropertyItemProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
> {
  store: Table<ID, R, DR>;

  /// the record being viewed
  record: R;

  /// the list of properties being viewed
  properties: (DataProperty | ObjectProperty)[];

  /// The component used to render the field
  DisplayComponent: React.ComponentType<DisplayInterface<any>>;

  // entity routes for foreign key navigation
  entityRoutes: EntityRoutes;
}

/**
 * A component that renders a nested property item.
 *
 * This component traverses through a chain of properties to display a deeply nested
 * property value from a record. It shows the last property label and renders the value
 * using the provided DisplayComponent.
 *
 * @template ID - The type of the record identifier (string or number)
 * @template R - The type of the generic record extending GenericRecord
 * @template DR - The type of the draft record extending DraftRecord
 * @template PF - The property field type constrained to keys of R
 * @template F - The field type constrained to keys of DR
 *
 * @param props - The component properties
 * @param props.store - The table store containing the record data
 * @param props.record - The record being viewed
 * @param props.properties - Array of properties defining the path to the nested value
 * @param props.DisplayComponent - React component used to render the field value
 *
 * @returns A JSX element displaying the nested property with its label and value
 *
 * @example
 * ```tsx
 * <ViewNestedPropertyItem
 *   store={userStore}
 *   record={user}
 *   properties={[addressProperty, streetProperty]}
 *   DisplayComponent={TextDisplay}
 * />
 * ```
 */
export const ViewNestedPropertyItem = observer(
  <
    ID extends string | number,
    R extends GenericRecord<ID, DR>,
    DR extends DraftRecord<ID>
  >({
    store,
    record,
    properties,
    DisplayComponent,
    entityRoutes,
  }: ViewNestedPropertyItemProps<ID, R, DR>) => {
    const prop = properties[properties.length - 1];
    const value = properties.reduce((currentValue, property) => {
      if (currentValue === null || currentValue === undefined) {
        return undefined;
      }
      return currentValue[property.tsName];
    }, record as any);

    return (
      <div>
        <Text size="sm" fw={550}>
          <MultiLingualString value={prop.label} />
        </Text>
        {value !== undefined && (
          <DisplayComponent
            db={store.db}
            property={prop}
            value={value}
            entityRoutes={entityRoutes}
          />
        )}
      </div>
    );
  }
);
