import { flexRender, Table as ReactTable } from "@tanstack/react-table";
import { MantineStyleProp, Paper, Text, Table, Stack } from "@mantine/core";
import { IconDatabaseOff } from "@tabler/icons-react";

export const COL_SELECT_ID = "__selectcol__";

const { Thead, Tr, Th, Tbody, Td } = Table;

export const SeraTableContent = <R,>(props: {
  selectedRowKeys: Record<string, boolean>;
  table: ReactTable<R>;
  bordered?: boolean;
  hasTopSection?: boolean;
  hasBottomSection?: boolean;
}) => {
  let tbody;

  if (props.table.getRowCount() === 0) {
    tbody = (
      <Tr key="empty-row">
        <Td colSpan={props.table.getVisibleLeafColumns().length}>
          <Stack justify="center" align="center" gap="xs">
            <IconDatabaseOff color={"var(--mantine-color-dimmed)"} />
            <Text c="dimmed" fz="sm">
              No records found.
            </Text>
          </Stack>
        </Td>
      </Tr>
    );
  } else {
    tbody = props.table.getRowModel().rows.map((row) => (
      <Tr
        key={row.id}
        bg={
          props.selectedRowKeys[row.id]
            ? "var(--mantine-color-blue-light)"
            : undefined
        }
      >
        {row.getVisibleCells().map((cell) => (
          <Td key={cell.id}>
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </Td>
        ))}
      </Tr>
    ));
  }

  const el = (
    <Table
      striped={true}
      highlightOnHover={true}
      verticalSpacing="xs"
      tabularNums={true}
    >
      <Thead>
        {props.table.getHeaderGroups().map((headerGroup) => (
          <Tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <Th
                key={header.id}
                w={header.id === COL_SELECT_ID ? "1%" : undefined}
              >
                {header.isPlaceholder
                  ? null
                  : flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
              </Th>
            ))}
          </Tr>
        ))}
      </Thead>
      <Tbody pos="relative">{tbody}</Tbody>
    </Table>
  );

  if (!props.bordered) return el;

  const style: MantineStyleProp = {};

  if (props.hasTopSection) {
    style.borderTopLeftRadius = 0;
    style.borderTopRightRadius = 0;
  }

  if (props.hasBottomSection) {
    style.borderBottomLeftRadius = 0;
    style.borderBottomRightRadius = 0;
  }

  return (
    <Paper withBorder={true} p={0} style={style}>
      {el}
    </Paper>
  );
};
