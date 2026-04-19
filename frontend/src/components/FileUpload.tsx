import { useRef, useState } from "react";
import { Upload, CheckCircle2 } from "lucide-react";

interface Props {
  label: string;
  accept: string;
  onFile: (file: File) => void;
  disabled?: boolean;
  done?: boolean;
  hint?: string;
}

export default function FileUpload({ label, accept, onFile, disabled, done, hint }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handle = (file: File | undefined) => {
    if (file) onFile(file);
  };

  return (
    <div
      className={`
        relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
        transition-all duration-200 select-none
        ${done
          ? "border-green-500 bg-green-900/20"
          : dragging
            ? "border-pokered bg-pokered/10 scale-[1.02]"
            : "border-pokeborder hover:border-pokered/60 bg-pokecard"}
        ${disabled ? "opacity-40 cursor-not-allowed" : ""}
      `}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handle(e.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        disabled={disabled}
        onChange={(e) => handle(e.target.files?.[0])}
      />

      {done ? (
        <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
      ) : (
        <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
      )}

      <p className="font-pixel text-[11px] text-gray-200">{label}</p>
      {hint && <p className="text-[10px] text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}
