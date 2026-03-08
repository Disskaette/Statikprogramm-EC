/**
 * AuflagerTable – displays support reactions (Auflagerkräfte) in a compact table.
 *
 * Shows max ULS (GZT) design reactions and max SLS (GZG) characteristic reactions
 * for each support A, B, C, … in kN.
 *
 * Values arrive from the backend in [N] and are converted to [kN] for display.
 */

import type { AuflagerKraefte } from "../../types/beam";

interface Props {
  data: AuflagerKraefte;
}

export function AuflagerTable({ data }: Props) {
  /** Convert [N] → [kN] formatted to 2 decimal places. */
  const toKN = (n: number) => (n / 1000).toFixed(2);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Auflagerkräfte
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 pr-4 font-medium text-gray-600">
                Auflager
              </th>
              <th className="text-right py-2 pr-4 font-medium text-gray-600">
                Charakteristisch [kN]
              </th>
              <th className="text-right py-2 font-medium text-gray-600">
                Design [kN]
              </th>
            </tr>
          </thead>
          <tbody>
            {data.labels.map((label, i) => (
              <tr
                key={label}
                className="border-b border-gray-100 last:border-0"
              >
                <td className="py-2 pr-4 font-mono font-bold text-gray-800">
                  {label}
                </td>
                <td className="py-2 pr-4 text-right text-gray-700">
                  {toKN(data.gzg_charakteristisch[i])}
                </td>
                <td className="py-2 text-right text-gray-700">
                  {toKN(data.gzt_design[i])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
