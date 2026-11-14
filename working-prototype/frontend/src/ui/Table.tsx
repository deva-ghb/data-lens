import type { KeyboardEvent, ReactNode } from "react";
import { cx } from "./cx";
import "./ui.css";

export type Column<Row> = {
  key: string;
  header: string;
  render: (row: Row) => ReactNode;
  numeric?: boolean;
  width?: number | string;
};

export type TableProps<Row> = {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  caption: string;
  onRowClick?: (row: Row) => void;
  emptyText?: string;
  /** On phones, show each row as a stacked block: first column as its title, others as label and value. */
  stackOnPhone?: boolean;
};

export function Table<Row>({
  columns,
  rows,
  rowKey,
  caption,
  onRowClick,
  emptyText = "Nothing to show yet.",
  stackOnPhone = true,
}: TableProps<Row>) {
  const activate = (row: Row) => (event: KeyboardEvent<HTMLTableRowElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick?.(row);
    }
  };
  return (
    <div className={cx("dl-table-wrap", stackOnPhone && "dl-table-wrap--stack")}>
      <table className="dl-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={cx(column.numeric === true && "dl-table__num")}
                style={column.width !== undefined ? { width: column.width } : undefined}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="dl-table__empty" colSpan={columns.length}>
                {emptyText}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={cx(onRowClick !== undefined && "dl-table__row--clickable")}
                onClick={onRowClick === undefined ? undefined : () => onRowClick(row)}
                onKeyDown={onRowClick === undefined ? undefined : activate(row)}
                tabIndex={onRowClick === undefined ? undefined : 0}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cx(column.numeric === true && "dl-table__num")}
                    data-label={column.header}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
