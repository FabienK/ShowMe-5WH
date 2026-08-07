interface LoaderProps {
  label?: string;
}

export function Loader({ label = "Chargement…" }: LoaderProps) {
  return (
    <div className="loader" role="status">
      <span className="loader__spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
