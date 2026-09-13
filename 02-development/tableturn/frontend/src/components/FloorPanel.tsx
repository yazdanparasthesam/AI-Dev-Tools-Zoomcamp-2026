import type { Party, Table, TableCreate, TableUpdate } from "../api/types";
import { AddTableForm } from "./AddTableForm";
import { TableCard } from "./TableCard";

interface FloorPanelProps {
  tables: Table[];
  parties: Party[];
  disabled?: boolean;
  onAddTable: (payload: TableCreate) => Promise<void>;
  onTurnTable: (table: Table) => void;
  onDeleteTable: (table: Table) => void;
  onUpdateTable: (table: Table, payload: TableUpdate) => void;
}

export function FloorPanel({
  tables,
  parties,
  disabled = false,
  onAddTable,
  onTurnTable,
  onDeleteTable,
  onUpdateTable,
}: FloorPanelProps) {
  const partyNameById = new Map(parties.map((party) => [party.id, party.name]));

  return (
    <section className="panel" aria-labelledby="floor-heading">
      <header className="panel__header">
        <h2 id="floor-heading">Floor</h2>
        <span className="pill">{tables.length} tables</span>
      </header>

      <AddTableForm onSubmit={onAddTable} disabled={disabled} />

      {tables.length === 0 ? (
        <p className="empty" data-testid="floor-empty">
          No tables yet. Add one to start seating guests.
        </p>
      ) : (
        <ul className="table-grid">
          {tables.map((table) => (
            <TableCard
              key={table.id}
              table={table}
              occupantName={
                table.occupied_by_party_id
                  ? (partyNameById.get(table.occupied_by_party_id) ?? null)
                  : null
              }
              disabled={disabled}
              onTurn={onTurnTable}
              onDelete={onDeleteTable}
              onUpdate={onUpdateTable}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
