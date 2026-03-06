import Editor from "@monaco-editor/react";

interface EditorPanelProps {
  value: string;
  onChange: (value: string) => void;
}

export default function EditorPanel({ value, onChange }: EditorPanelProps) {
  return (
    <div style={{ flex: 1, overflow: "hidden", height: "100%" }}>
      <Editor
        language="python"
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        height="100%"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
