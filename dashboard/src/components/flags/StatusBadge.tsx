import { Badge } from "@/components/ui/badge";

const VARIANTS: Record<
  string,
  "success" | "secondary" | "warning" | "outline"
> = {
  active: "success",
  draft: "secondary",
  archived: "outline",
  disabled: "warning",
};

export function FlagStatusBadge({ status }: { status: string }) {
  const variant = VARIANTS[status] ?? "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}
