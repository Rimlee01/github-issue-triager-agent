import { useState } from "react";

export function Button({ children, variant = "primary", size = "md", disabled, onClick, type = "button", style = {} }) {
  const base = {
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "6px",
    borderRadius: "6px", fontWeight: 500, cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.7 : 1,
    transition: "background 0.15s, border-color 0.15s, transform 0.12s, box-shadow 0.15s, filter 0.15s",
    fontSize: size === "sm" ? "12px" : "14px",
    padding: size === "sm" ? "3px 10px" : "5px 16px",
    lineHeight: "20px", border: "1px solid",
  };

  const variants = {
    primary: { background: "var(--color-success-emphasis)", color: "#fff", borderColor: "rgba(31,35,40,0.15)" },
    default: { background: "var(--color-canvas-default)", color: "var(--color-fg-default)", borderColor: "var(--color-border-default)" },
    danger: { background: "var(--color-danger-emphasis)", color: "#fff", borderColor: "rgba(31,35,40,0.15)" },
    accent: { background: "var(--color-accent-emphasis)", color: "#fff", borderColor: "rgba(31,35,40,0.15)" },
    ghost: { background: "transparent", color: "var(--color-fg-muted)", borderColor: "transparent" },
  };

  return (
    <button type={type} onClick={onClick} disabled={disabled}
      style={{ ...base, ...variants[variant] || variants.default, ...style }}>
      {children}
    </button>
  );
}

export function Label({ children, variant = "default" }) {
  const variants = {
    default: { bg: "var(--color-neutral-subtle)", color: "var(--color-fg-muted)", border: "var(--color-border-default)" },
    bug: { bg: "#ffebe9", color: "#cf222e", border: "#ff818266" },
    feature: { bg: "#ddf4ff", color: "#0969da", border: "#79c0ff66" },
    security: { bg: "#ffebe9", color: "#cf222e", border: "#ff818266" },
    performance: { bg: "#fff8c5", color: "#9a6700", border: "#f2cc6066" },
    documentation: { bg: "#f6f8fa", color: "#57606a", border: "#d0d7de" },
    question: { bg: "#ddf4ff", color: "#0969da", border: "#79c0ff66" },
  };
  const v = variants[variant] || variants.default;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", padding: "0 7px",
      fontSize: "12px", fontWeight: 500, lineHeight: "20px", whiteSpace: "nowrap",
      borderRadius: "100px", border: `1px solid ${v.border}`,
      background: v.bg, color: v.color,
    }}>
      {children}
    </span>
  );
}

export function Input({ value, onChange, placeholder, disabled, type = "text", style = {} }) {
  return (
    <input type={type} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled}
      style={{
        width: "100%", padding: "5px 12px", lineHeight: "20px",
        background: "var(--color-canvas-default)",
        border: "1px solid var(--color-border-default)",
        borderRadius: "6px", color: "var(--color-fg-default)",
        fontSize: "14px", outline: "none", ...style,
      }}
    />
  );
}

export function Textarea({ value, onChange, placeholder, disabled, rows = 5 }) {
  return (
    <textarea value={value} onChange={onChange} placeholder={placeholder} disabled={disabled} rows={rows}
      style={{
        width: "100%", padding: "5px 12px", lineHeight: "20px",
        background: "var(--color-canvas-default)",
        border: "1px solid var(--color-border-default)",
        borderRadius: "6px", color: "var(--color-fg-default)",
        fontSize: "14px", resize: "vertical", outline: "none",
        fontFamily: "var(--font-sans)",
      }}
    />
  );
}

export function Spinner({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none"
      style={{ animation: "spin 0.75s linear infinite", flexShrink: 0 }}>
      <circle cx="8" cy="8" r="6" stroke={color} strokeWidth="1.5" strokeOpacity="0.25"/>
      <path d="M14 8a6 6 0 00-6-6" stroke={color} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export function ProgressBar({ value, color }) {
  return (
    <div style={{ height: "8px", background: "var(--color-border-muted)", borderRadius: "100px", overflow: "hidden" }}>
      <div style={{
        height: "100%", width: `${Math.round(value * 100)}%`,
        background: color || "var(--color-accent-emphasis)",
        borderRadius: "100px", transition: "width 0.5s ease",
      }}/>
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button variant="default" size="sm" onClick={() => {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }}>
      {copied ? "✓ Copied!" : label}
    </Button>
  );
}
