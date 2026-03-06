interface RunButtonProps {
  onClick: () => void;
  disabled: boolean;
}

export default function RunButton({ onClick, disabled }: RunButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="bg-[#a6e3a1] text-[#1e1e2e] font-bold px-4 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed"
    >
      ▶ Run Code
    </button>
  );
}
