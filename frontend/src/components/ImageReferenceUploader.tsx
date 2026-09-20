import { useRef, useState } from "react";
import { CloseIcon, UploadIcon } from "./icons";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];

interface ImageReferenceUploaderProps {
  value: string | null;
  onChange: (dataUrl: string | null) => void;
  disabled?: boolean;
}

export function ImageReferenceUploader({ value, onChange, disabled }: ImageReferenceUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) return;

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Unsupported format (PNG, JPEG, or WebP only).");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("Image too large (10 MB max).");
      return;
    }

    setError(null);
    const reader = new FileReader();
    reader.onload = () => onChange(reader.result as string);
    reader.readAsDataURL(file);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    if (disabled) return;
    handleFile(event.dataTransfer.files[0]);
  }

  if (value) {
    return (
      <div className="image-reference-uploader">
        <div className="image-reference-uploader__preview">
          <img src={value} alt="Selected reference image" />
          <button
            type="button"
            className="image-reference-uploader__remove"
            onClick={() => onChange(null)}
            disabled={disabled}
            aria-label="Remove the reference image"
          >
            <CloseIcon />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="image-reference-uploader">
      <div
        className={`image-reference-uploader__dropzone${
          dragOver ? " image-reference-uploader__dropzone--dragover" : ""
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <UploadIcon />
        <p>Drag and drop an image, or click to choose one</p>
        <span className="image-reference-uploader__hint">PNG, JPEG, or WebP · 10 MB max</span>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="image-reference-uploader__input"
        disabled={disabled}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      {error && (
        <p className="image-reference-uploader__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
