import { useContext, useEffect, useMemo } from "react";
import { DisplayInterface, EntityRoute, EntityRoutes } from ".";
import { observer } from "mobx-react-lite";
import { DB, ObjectProperty } from "sera-db";
import { Group, Text } from "@mantine/core";
import { NotFoundInline } from "../../basic/Transition";
import { ExternalComponentContext } from "../../basic/ExternalComponent";

function useForeignKeyDisplay<ID extends string | number>(
  db: DB,
  property: ObjectProperty,
  ids: ID[],
  entityRoutes: EntityRoutes
): [Record<ID, any>, EntityRoute] {
  const table = db.getByName(property.targetClass);
  const route = entityRoutes[property.targetClass];

  useEffect(() => {
    table.fetchByIds(ids);
  }, [ids]);

  const records = {} as Record<ID, any>;
  for (const id of ids) {
    records[id] = table.get(id);
  }
  return [records, route];
}

export const SingleForeignKeyDisplay = observer(
  <ID extends string | number>({
    db,
    property,
    value,
    entityRoutes,
  }: DisplayInterface<ID>) => {
    const { link: Link } = useContext(ExternalComponentContext);

    const ids = useMemo(() => {
      return [value];
    }, [value]);

    const [records, route] = useForeignKeyDisplay(
      db,
      property as ObjectProperty,
      ids,
      entityRoutes
    );
    const record = records[value];

    if (record === undefined) {
      return <Text size="sm">{value}</Text>;
    }

    if (record === null) {
      return <NotFoundInline />;
    }

    if (route === undefined) {
      return <Text size="sm">{record.name}</Text>;
    }

    return (
      <Link to={route.to} openInNewPage={false} params={{ id: record.id }}>
        {record.name}
      </Link>
    );
  }
);

export const MultiForeignKeyDisplay = observer(
  <ID extends string | number>({
    db,
    property,
    value,
    entityRoutes,
  }: DisplayInterface<ID[]>) => {
    const { link: Link } = useContext(ExternalComponentContext);
    const [records, route] = useForeignKeyDisplay(
      db,
      property as ObjectProperty,
      value,
      entityRoutes
    );

    return (
      <Group gap="xs">
        {value.map((id, index) => {
          const record = records[id];
          if (record === undefined) {
            return (
              <Text size="sm" key={id}>
                {value}
              </Text>
            );
          }
          if (record === null) {
            return <NotFoundInline key={id} />;
          }

          if (route === undefined) {
            return (
              <Text size="sm" key={index}>
                {record.name}
              </Text>
            );
          }
          return (
            <Link
              key={index}
              to={route.to}
              openInNewPage={false}
              params={{ id: record.id }}
            >
              {record.name}
            </Link>
          );
        })}
      </Group>
    );
  }
);
