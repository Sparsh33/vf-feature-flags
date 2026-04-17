import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Pencil, Plus, Sparkles, Trash2 } from "lucide-react";

import { FlagStatusBadge } from "@/components/flags/StatusBadge";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDeleteFlag, useFlagsList } from "@/hooks/useFlags";
import { toast } from "@/hooks/use-toast";

const PAGE_SIZE = 20;

export default function FlagsListPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [page, setPage] = React.useState(0);
  const [pendingDeleteId, setPendingDeleteId] = React.useState<string | null>(
    null
  );

  const params = {
    limit: PAGE_SIZE,
    skip: page * PAGE_SIZE,
    status: statusFilter === "all" ? undefined : statusFilter,
  };
  const { data, isLoading, isError } = useFlagsList(params);
  const deleteFlag = useDeleteFlag();

  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleDelete = async () => {
    if (!pendingDeleteId) return;
    try {
      await deleteFlag.mutateAsync(pendingDeleteId);
      toast({ title: "Flag deleted" });
      setPendingDeleteId(null);
    } catch {
      toast({
        title: "Delete failed",
        description: "Could not delete flag.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Flags</h1>
          <p className="text-sm text-muted-foreground">
            Manage your feature flags and cohort rollouts.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/chat">
              <Sparkles className="mr-2 h-4 w-4" />
              Build with AI
            </Link>
          </Button>
          <Button onClick={() => navigate("/flags/new")}>
            <Plus className="mr-2 h-4 w-4" />
            New flag
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
          <div>
            <CardTitle className="text-base">All flags</CardTitle>
            <CardDescription>
              {total} total {total === 1 ? "flag" : "flags"}
            </CardDescription>
          </div>
          <div className="w-40">
            <Select
              value={statusFilter}
              onValueChange={(value) => {
                setStatusFilter(value);
                setPage(0);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Cohorts</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-muted-foreground"
                  >
                    Loading…
                  </TableCell>
                </TableRow>
              ) : isError ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-destructive"
                  >
                    Failed to load flags.
                  </TableCell>
                </TableRow>
              ) : data && data.flags.length > 0 ? (
                data.flags.map((flag) => (
                  <TableRow key={flag.id}>
                    <TableCell className="font-mono text-xs">
                      {flag.flag_key}
                    </TableCell>
                    <TableCell className="font-medium">{flag.name}</TableCell>
                    <TableCell>
                      <FlagStatusBadge status={flag.status} />
                    </TableCell>
                    <TableCell>{flag.cohorts.length}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(flag.updated_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => navigate(`/flags/${flag.id}`)}
                          aria-label="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setPendingDeleteId(flag.id)}
                          aria-label="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-muted-foreground"
                  >
                    No flags yet. Create your first one.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {pageCount > 1 ? (
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Page {page + 1} of {pageCount}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page + 1 >= pageCount}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <AlertDialog
        open={pendingDeleteId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this flag?</AlertDialogTitle>
            <AlertDialogDescription>
              The flag will be soft-deleted. Existing evaluations will stop
              returning this key.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
