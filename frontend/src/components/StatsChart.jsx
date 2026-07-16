import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";

const CATEGORY_COLORS = {
  bug: "#cf222e", security: "#cf222e", performance: "#bf8700",
  feature_request: "#0969da", documentation: "#57606a", question: "#0969da", unknown: "#57606a",
};
const PRIORITY_COLORS = {
  critical: "#cf222e", high: "#bf8700", medium: "#0969da", low: "#1f883d",
};

export default function StatsChart({ history }) {
  const categoryData = useMemo(() => {
    const counts = {};
    history.forEach(h => { counts[h.category] = (counts[h.category] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({
      name: name.replace("_", " "), value, fill: CATEGORY_COLORS[name] || "#57606a"
    }));
  }, [history]);

  const priorityData = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    history.forEach(h => { if (h.priority in counts) counts[h.priority]++; });
    return Object.entries(counts).filter(([, v]) => v > 0).map(([name, value]) => ({ name, value }));
  }, [history]);

  if (history.length === 0) return null;

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#8b949e" : "#57606a";
  const gridColor = isDark ? "#21262d" : "#d0d7de";

  const tooltipStyle = {
    fontSize: "12px",
    background: isDark ? "#161b22" : "#fff",
    border: `1px solid ${isDark ? "#30363d" : "#d0d7de"}`,
    borderRadius: "6px",
    color: isDark ? "#e6edf3" : "#1f2328",
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
      <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", padding: "16px" }}>
        <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "14px" }}>
          Issues by category
        </div>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={categoryData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} cursor={{ fill: isDark ? "#21262d" : "#f6f8fa" }} />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {categoryData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ background: "var(--color-canvas-default)", border: "1px solid var(--color-border-default)", borderRadius: "6px", padding: "16px" }}>
        <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "14px" }}>
          Priority distribution
        </div>
        <ResponsiveContainer width="100%" height={150}>
          <PieChart>
            <Pie data={priorityData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={3} dataKey="value">
              {priorityData.map((entry, i) => <Cell key={i} fill={PRIORITY_COLORS[entry.name] || "#57606a"} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: "12px", color: textColor }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


