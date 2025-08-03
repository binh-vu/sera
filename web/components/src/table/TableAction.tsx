import {
  IconDatabaseImport,
  IconDownload,
  IconPencil,
  IconPlus,
  IconReload,
} from "@tabler/icons-react";
import { Button, Group, MantineSize } from "@mantine/core";

export interface SeraActionConfig<ID extends string | number> {
  add?: () => void;
  edit?: (id: ID) => void;
  delete?: () => void;
  export?: () => void;
  reload?: boolean;
  import?: () => void;
}

/// Action related to the table such as add, edit, delete, export, etc.
export const SeraTableAction = <ID extends string | number>({
  actions,
  reloadData,
  selectedRowKeys,
  size = "xs",
}: {
  size?: MantineSize;
  actions?: SeraActionConfig<ID>;
  reloadData?: () => void;
  selectedRowKeys: ID[];
}) => {
  return (
    <Group gap={size}>
      {actions?.add && (
        <Button
          variant="light"
          leftSection={<IconPlus size={16} stroke={1.5} />}
          size={size}
          onClick={actions.add}
        >
          Add
        </Button>
      )}
      {actions?.edit && (
        <Button
          leftSection={<IconPencil size={16} stroke={1.5} />}
          size={size}
          variant="light"
          onClick={() => actions.edit !== undefined && actions.edit(selectedRowKeys[0])}
          disabled={selectedRowKeys.length !== 1}
        >
          Edit
        </Button>
      )}
      {actions?.reload && (
        <Button
          leftSection={<IconReload size={16} stroke={1.5} />}
          size={size}
          onClick={reloadData}
          variant="light"
        >
          Reload
        </Button>
      )}
      {actions?.import && (
        <Button
          leftSection={<IconDatabaseImport size={16} stroke={1.5} />}
          size={size}
          variant="light"
          onClick={actions.import}
        >
          Import
        </Button>
      )}
      {actions?.export && (
        <Button
          leftSection={<IconDownload size={16} stroke={1.5} />}
          size={size}
          variant="light"
          onClick={actions.export}
        >
          Export
        </Button>
      )}
    </Group>
  );
};

/// Check if the table enables actions such as add, edit, delete, export, etc.
export const hasAction = <ID extends string | number>(actions?: SeraActionConfig<ID>) => {
  return (
    actions !== undefined &&
    (actions.add !== undefined ||
      actions.edit !== undefined ||
      actions.delete !== undefined ||
      actions.export !== undefined ||
      actions.reload === true ||
      actions.import !== undefined)
  );
};
