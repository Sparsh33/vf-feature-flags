import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";

export function Header() {
  const { user } = useAuth();
  return (
    <header className="flex h-16 items-center justify-end gap-3 border-b bg-background px-6">
      {user ? (
        <>
          <span className="text-sm text-muted-foreground">{user.email}</span>
          <Badge variant="secondary">{user.role}</Badge>
        </>
      ) : null}
    </header>
  );
}
