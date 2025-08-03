import { observer } from "mobx-react-lite";
import {
  ClassName,
  DataProperty,
  DraftRecord,
  GenericRecord,
  ObjectProperty,
  Table,
} from "sera-db";
import { Text } from "@mantine/core";
import { MultiLingualString } from "../basic";
import { DisplayInterface } from "../data/display";
import { NoQueryArgsPathDef } from "sera-route";

export interface ViewItemProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>
> {
  store: Table<ID, R, DR>;

  /// the record being viewed
  record: R;

  /// the property being viewed
  property: DataProperty | ObjectProperty;

  /// The component used to render the field
  DisplayComponent: React.ComponentType<DisplayInterface<any>>;

  /// Entity routes for navigation
  entityRoutes: EntityRoutes;
}

export const ViewItem = observer(
  <
    ID extends string | number,
    R extends GenericRecord<ID, DR>,
    DR extends DraftRecord<ID>
  >({
    store,
    record,
    property,
    DisplayComponent,
    entityRoutes,
  }: ViewItemProps<ID, R, DR>) => {
    const value = (record as any)[property.tsName];

    return (
      <div>
        <Text size="sm" fw={500}>
          <MultiLingualString value={property.label} />
        </Text>
        <DisplayComponent
          db={store.db}
          entityRoutes={entityRoutes}
          property={property}
          value={value}
        />
      </div>
    );
  }
);
