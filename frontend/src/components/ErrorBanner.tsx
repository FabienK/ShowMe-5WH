import type { ApiError } from "../types";

interface ErrorBannerProps {
  error: ApiError;
}

export function ErrorBanner({ error }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <strong>Error.</strong> {error.detail}
    </div>
  );
}
