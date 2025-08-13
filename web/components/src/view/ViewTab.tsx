import { DraftRecord, GenericRecord, Schema, SchemaType, Table } from "sera-db";
import { Tabs } from "@mantine/core";
import { FieldGroup, SeraView } from "./View";
import { EntityRoutes } from "../data";

export interface SeraViewTabProps<
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
> {
  // record schema
  schema: Schema<ID, R, DR, PF, F, ST>;

  // the store that contains records
  store: Table<ID, R, DR>;

  // layout of the fields
  fieldTabs: {
    tabName: string;
    fieldGroups: FieldGroup<ID, R, DR, PF, F, ST>[];
  }[];

  // the record being viewed
  record: R;

  // styling for the form
  tabStyles?: React.CSSProperties;

  tabClassName?: string;

  // entity routes for foreign key navigation
  entityRoutes: EntityRoutes;
}

export const SeraViewTab = <
  ID extends string | number,
  R extends GenericRecord<ID, DR>,
  DR extends DraftRecord<ID>,
  PF extends keyof R,
  F extends keyof DR,
  ST extends SchemaType<ID, R, DR, PF, F>
>(
  props: SeraViewTabProps<ID, R, DR, PF, F, ST>
) => {
  return (
    <Tabs defaultValue={props.fieldTabs[0].tabName}>
      <Tabs.List>
        {props.fieldTabs.map((tab, index) => (
          <Tabs.Tab key={index} value={tab.tabName}>
            {tab.tabName}
          </Tabs.Tab>
        ))}
      </Tabs.List>
      {props.fieldTabs.map((tab, index) => (
        <Tabs.Panel key={index} value={tab.tabName} pt="sm">
          <SeraView
            schema={props.schema}
            store={props.store}
            record={props.record}
            fieldGroups={tab.fieldGroups}
            styles={props.tabStyles}
            className={props.tabClassName}
            entityRoutes={props.entityRoutes}
          />
        </Tabs.Panel>
      ))}
    </Tabs>
  );
};
