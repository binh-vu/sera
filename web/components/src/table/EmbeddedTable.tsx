import { useMemo, useState } from "react";
import {
  ColumnDef,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Checkbox, Flex, Group, Paper, Text } from "@mantine/core";
import { SeraColumn } from "./makeColumns";
import { hasAction, SeraActionConfig, SeraTableAction } from "./TableAction";
import { SeraTableContent } from "./TableContent";
import { TablePagination } from "./TablePagination";

export interface SeraEmbeddedTableProps<R> {
  // position of the pagination
  pagination?: {
    positions?: Set<"topRight" | "bottomLeft" | "bottomCenter" | "bottomRight">;
    showSizeChanger?: boolean;
  };
  // list of columns to display
  columns: SeraColumn[];
  // data
  data: R[];
  // predefined actions that can be performed on the table
  actions?: SeraActionConfig<number>;
}

export const DEFAULT_PAGINATION_POSITIONS = new Set<"topRight" | "bottomLeft" | "bottomRight">([
  "topRight",
  "bottomRight",
]);

export const SeraEmbeddedTable = <R,>(props: SeraEmbeddedTableProps<R>) => {
  const [selectedRowKeys, setSelectedRowKeys] = useState({} as Record<string, boolean>);

  // render the table
  const columns: ColumnDef<R>[] = useMemo(() => {
    const columns: ColumnDef<R>[] = [
      {
        id: "selection",
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllRowsSelected()}
            indeterminate={table.getIsSomeRowsSelected()}
            onChange={table.getToggleAllRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
          />
        ),
      },
    ];
    props.columns.forEach((column) => {
      columns.push({
        id: column.key,
        header: column.title as any,
        accessorFn: column.render,
        cell: ({ row }) => {
          return column.render(row.original);
        },
      });
    });
    return columns;
  }, [props.columns]);

  const table = useReactTable({
    data: props.data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      rowSelection: selectedRowKeys,
    },
    onRowSelectionChange: setSelectedRowKeys,
  });

  const listSelectedRowKeys = useMemo(() => {
    return Object.keys(selectedRowKeys)
      .filter((key) => selectedRowKeys[key])
      .map(Number);
  }, [selectedRowKeys]);

  // the top section of the table is often reserved for actions and pagination
  let topSection = undefined;
  // bottom section of the table is reserved for pagination
  let bottomSection = undefined;

  if (hasAction(props.actions)) {
    topSection = <SeraTableAction actions={props.actions} selectedRowKeys={listSelectedRowKeys} />;
  }

  const paginationPositions = props.pagination?.positions || DEFAULT_PAGINATION_POSITIONS;
  if (paginationPositions.size > 0) {
    const pagination = table.getState().pagination;

    const pgnEl = (
      <TablePagination
        total={table.getPageCount()}
        pageIndex={pagination.pageIndex}
        pageSize={pagination.pageSize}
        onUpdatePagination={(pageIndex: number, pageSize: number) =>
          table.setPagination({ pageIndex, pageSize })
        }
        allowPageSizeChange={props.pagination?.showSizeChanger}
      />
    );

    if (paginationPositions.has("topRight")) {
      if (topSection !== undefined) {
        topSection = (
          <Group justify="space-between" gap="sm">
            {topSection}
            {pgnEl}
          </Group>
        );
      } else {
        topSection = <Flex justify="flex-end">{pgnEl}</Flex>;
      }
    }

    if (
      paginationPositions.has("bottomRight") ||
      paginationPositions.has("bottomLeft") ||
      paginationPositions.has("bottomCenter")
    ) {
      // Determine position of pagination at bottom
      if (paginationPositions.has("bottomLeft")) {
        bottomSection = (
          <Flex justify="space-between" align="center">
            {pgnEl}
            <Text size="sm" c="dimmed">
              Showing {pagination.pageIndex * pagination.pageSize + 1} to{" "}
              {Math.min((pagination.pageIndex + 1) * pagination.pageSize, props.data.length)} of{" "}
              {props.data.length} records
            </Text>
          </Flex>
        );
      } else {
        bottomSection = (
          <Flex justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              Showing {pagination.pageIndex * pagination.pageSize + 1} to{" "}
              {Math.min((pagination.pageIndex + 1) * pagination.pageSize, props.data.length)} of{" "}
              {props.data.length} records
            </Text>
            {pgnEl}
          </Flex>
        );
      }
    }
  }

  const tableEl = (
    <SeraTableContent
      selectedRowKeys={selectedRowKeys}
      table={table}
      bordered={true}
      hasTopSection={topSection !== undefined}
      hasBottomSection={bottomSection !== undefined}
    />
  );

  if (topSection === undefined && bottomSection === undefined) {
    return tableEl;
  } else {
    return (
      <div>
        {topSection !== undefined && (
          <Paper
            withBorder={true}
            p="xs"
            style={{
              borderBottomLeftRadius: 0,
              borderBottomRightRadius: 0,
              borderBottom: "none",
            }}
          >
            {topSection}
          </Paper>
        )}
        {tableEl}
        {bottomSection !== undefined && (
          <Paper
            withBorder={true}
            p="xs"
            style={{
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
              borderTop: "none",
            }}
          >
            {bottomSection}
          </Paper>
        )}
      </div>
    );
  }
};
