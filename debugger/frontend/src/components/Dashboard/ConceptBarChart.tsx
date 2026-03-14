import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { ConceptStatItem } from "../../api/client";

interface ConceptBarChartProps {
  data: ConceptStatItem[];
}

export default function ConceptBarChart({ data }: ConceptBarChartProps) {
  const chartData = data.map((item) => ({ name: item.concept, errors: item.error_count }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" tick={{ fill: "#a6adc8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#a6adc8", fontSize: 12 }} />
        <Tooltip
          contentStyle={{ background: "#181825", border: "1px solid #313244", color: "#cdd6f4" }}
          cursor={{ fill: "#313244" }}
        />
        <Bar dataKey="errors" fill="#f38ba8" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
