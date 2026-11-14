import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { Loaded, titleCase } from "./common";
import "./pages.css";
import "./warnings.css";

type DistrictData = { district: string; period_days: number; threshold: number; columns: string[]; rows: { syndrome: string; cells: { zone: string; value: number | null }[]; total: number }[] };
type Employers = { threshold: number; employers: string[]; rows: { measure: string; cells: { employer: string; value: number | null }[]; total: number }[] };

export function District() {
  const district = useGet<DistrictData>("/api/district");
  const employers = useGet<Employers>("/api/authority/employers");
  return (
    <Page title="District view" subtitle="Clinic visits by place, across employers. Any group under the threshold is hidden and totals are rounded to the nearest 5.">
      <Loaded query={district}>
        {(d) => (
          <Card title={`${d.district}, last ${d.period_days} days`} subtitle={`Groups under ${d.threshold} are hidden`} flush>
            <div className="dl-table-wrap">
              <table className="dl-table">
                <caption className="visually-hidden">Clinic visits by syndrome and place</caption>
                <thead>
                  <tr>
                    <th scope="col">Reason for visit</th>
                    {d.columns.map((c) => <th key={c} scope="col" className="dl-table__num">{c}</th>)}
                    <th scope="col" className="dl-table__num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {d.rows.map((r) => (
                    <tr key={r.syndrome}>
                      <td className="row-head">{titleCase(r.syndrome)}</td>
                      {r.cells.map((c) => (
                        <td key={c.zone} className="dl-table__num num">{c.value === null ? <span className="suppressed">Hidden</span> : c.value}</td>
                      ))}
                      <td className="dl-table__num num"><strong>{r.total}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </Loaded>
      <Loaded query={employers}>
        {(e) => (
          <Card title="By employer" subtitle={`Workers and next shift tiers, groups under ${e.threshold} hidden`} flush>
            <div className="dl-table-wrap">
              <table className="dl-table">
                <caption className="visually-hidden">Employer totals</caption>
                <thead>
                  <tr>
                    <th scope="col">Measure</th>
                    {e.employers.map((n) => <th key={n} scope="col" className="dl-table__num">{n}</th>)}
                    <th scope="col" className="dl-table__num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {e.rows.map((r) => (
                    <tr key={r.measure}>
                      <td className="row-head">{r.measure}</td>
                      {r.cells.map((c) => <td key={c.employer} className="dl-table__num num">{c.value === null ? <span className="suppressed">Hidden</span> : c.value}</td>)}
                      <td className="dl-table__num num"><strong>{r.total}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </Loaded>
    </Page>
  );
}
