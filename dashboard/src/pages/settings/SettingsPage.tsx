import * as React from "react";
import { AxiosError } from "axios";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsPage() {
  const { user } = useAuth();
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [newKey, setNewKey] = React.useState<string | null>(null);
  const [rotating, setRotating] = React.useState(false);

  const handleRotate = async () => {
    setRotating(true);
    try {
      const response = await authApi.rotateApiKey();
      setNewKey(response.api_key);
      setConfirmOpen(false);
    } catch (err) {
      const detail =
        err instanceof AxiosError
          ? (err.response?.data as { detail?: string } | undefined)?.detail
          : undefined;
      toast({
        title: "Rotate failed",
        description: detail ?? "Unable to rotate API key.",
        variant: "destructive",
      });
    } finally {
      setRotating(false);
    }
  };

  const handleCopy = () => {
    if (newKey) {
      void navigator.clipboard.writeText(newKey);
      toast({ title: "Copied", description: "API key copied to clipboard." });
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your workspace credentials.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workspace</CardTitle>
          <CardDescription>
            Displayed on the evaluation API and in audit logs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label>Signed in as</Label>
            <p className="font-mono text-sm">{user?.email ?? "—"}</p>
          </div>
          <div className="space-y-1">
            <Label>Client ID</Label>
            <p className="font-mono text-sm">{user?.client_id ?? "—"}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">API key</CardTitle>
          <CardDescription>
            Used for the `X-Client-API-Key` header on the evaluation API.
            Rotating will invalidate the previous key immediately.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Your current key is hidden. Rotate to generate a fresh one.
          </p>
          <Button
            variant="destructive"
            onClick={() => setConfirmOpen(true)}
            disabled={rotating}
          >
            Rotate API key
          </Button>
        </CardContent>
      </Card>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rotate API key?</AlertDialogTitle>
            <AlertDialogDescription>
              The previous key stops working immediately. Any service still
              using it will fail until you deploy the new key.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRotate} disabled={rotating}>
              {rotating ? "Rotating…" : "Rotate"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog
        open={newKey !== null}
        onOpenChange={(open) => {
          if (!open) setNewKey(null);
        }}
      >
        <DialogContent
          onInteractOutside={(e) => e.preventDefault()}
          onEscapeKeyDown={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>New API key</DialogTitle>
            <DialogDescription>
              Save this now — we won&apos;t be able to show it to you again.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md border bg-muted p-3 font-mono text-sm break-all">
            {newKey}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleCopy}>
              Copy
            </Button>
            <Button onClick={() => setNewKey(null)}>
              I&apos;ve saved this
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
