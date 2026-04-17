import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AxiosError } from "axios";
import { ArrowLeft } from "lucide-react";

import {
  CohortEditor,
  newCohortRow,
  type CohortRow,
  validateCohortRows,
} from "@/components/flags/CohortEditor";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateFlag, useFlag, useUpdateFlag } from "@/hooks/useFlags";
import { toast } from "@/hooks/use-toast";
import { formatJson, tryParseJson } from "@/lib/json";
import type { Cohort, FlagCreateRequest, FlagUpdateRequest } from "@/types/api";

const FLAG_KEY_REGEX = /^[a-z0-9_-]+$/;

export default function FlagEditorPage() {
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === "new";
  const navigate = useNavigate();

  const existing = useFlag(isNew ? undefined : id);
  const createMutation = useCreateFlag();
  const updateMutation = useUpdateFlag(id ?? "");

  const [flagKey, setFlagKey] = React.useState("");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [defaultValueText, setDefaultValueText] = React.useState("null");
  const [paramsSchemaText, setParamsSchemaText] = React.useState("");
  const [showParamsSchema, setShowParamsSchema] = React.useState(false);
  const [rows, setRows] = React.useState<CohortRow[]>([]);
  const [hasLoaded, setHasLoaded] = React.useState(false);

  // Populate form from loaded flag (edit mode) once.
  React.useEffect(() => {
    if (isNew || hasLoaded || !existing.data) return;
    const flag = existing.data;
    setFlagKey(flag.flag_key);
    setName(flag.name);
    setDescription(flag.description ?? "");
    setDefaultValueText(formatJson(flag.default_value));
    if (flag.parameters_schema) {
      setParamsSchemaText(formatJson(flag.parameters_schema));
      setShowParamsSchema(true);
    }
    setRows(
      flag.cohorts.map((cohort) =>
        newCohortRow({
          id: cohort.id,
          name: cohort.name,
          percentage: cohort.percentage,
          valueText: formatJson(cohort.value),
        })
      )
    );
    setHasLoaded(true);
  }, [existing.data, isNew, hasLoaded]);

  const defaultValueParsed = tryParseJson(defaultValueText);
  const paramsSchemaParsed = showParamsSchema
    ? tryParseJson(paramsSchemaText)
    : { ok: true, value: null };
  const cohortCheck = validateCohortRows(rows);

  const flagKeyValid = isNew ? FLAG_KEY_REGEX.test(flagKey) : true;
  const saveDisabled =
    !name.trim() ||
    (isNew && (!flagKey.trim() || !flagKeyValid)) ||
    !defaultValueParsed.ok ||
    !paramsSchemaParsed.ok ||
    !cohortCheck.valid;

  const buildCohorts = (): Cohort[] =>
    rows.map((row) => ({
      id: row.id,
      name: row.name.trim(),
      percentage: row.percentage,
      value: tryParseJson(row.valueText).value,
    }));

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (saveDisabled) return;
    const parametersSchema =
      showParamsSchema && paramsSchemaText.trim()
        ? (paramsSchemaParsed.value as Record<string, unknown>)
        : undefined;
    try {
      if (isNew) {
        const payload: FlagCreateRequest = {
          flag_key: flagKey.trim(),
          name: name.trim(),
          description: description.trim() || undefined,
          default_value: defaultValueParsed.value,
          cohorts: buildCohorts(),
          parameters_schema: parametersSchema,
        };
        const created = await createMutation.mutateAsync(payload);
        toast({ title: "Flag created", description: created.flag_key });
        navigate(`/flags/${created.id}`, { replace: true });
      } else if (id) {
        const payload: FlagUpdateRequest = {
          name: name.trim(),
          description: description.trim() || undefined,
          default_value: defaultValueParsed.value,
          cohorts: buildCohorts(),
          parameters_schema: parametersSchema,
        };
        await updateMutation.mutateAsync(payload);
        toast({ title: "Flag updated" });
      }
    } catch (err) {
      const detail =
        err instanceof AxiosError
          ? (err.response?.data as { detail?: string } | undefined)?.detail
          : undefined;
      toast({
        title: "Save failed",
        description: detail ?? "Unable to save flag.",
        variant: "destructive",
      });
    }
  };

  if (!isNew && existing.isLoading) {
    return (
      <div className="p-8 text-center text-sm text-muted-foreground">
        Loading flag…
      </div>
    );
  }
  if (!isNew && existing.isError) {
    return (
      <div className="p-8 text-center text-sm text-destructive">
        Could not load flag.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => navigate("/flags")}
      >
        <ArrowLeft className="mr-1 h-4 w-4" /> Back to flags
      </Button>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>{isNew ? "New flag" : "Edit flag"}</CardTitle>
            <CardDescription>
              Configure the flag metadata, default value, and cohorts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="flag_key">Flag key</Label>
              <Input
                id="flag_key"
                className="font-mono"
                value={flagKey}
                onChange={(e) => setFlagKey(e.target.value)}
                disabled={!isNew}
                placeholder="example_flag_key"
              />
              <p className="text-xs text-muted-foreground">
                Allowed: lowercase letters, digits, underscores, hyphens
                (regex: <span className="font-mono">[a-z0-9_-]+</span>).
              </p>
              {isNew && flagKey && !flagKeyValid ? (
                <p className="text-xs text-destructive">
                  Flag key must match [a-z0-9_-]+
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Human-readable name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default_value">Default value (JSON)</Label>
              <Textarea
                id="default_value"
                className="font-mono text-xs"
                rows={4}
                value={defaultValueText}
                onChange={(e) => setDefaultValueText(e.target.value)}
              />
              {!defaultValueParsed.ok ? (
                <p className="text-xs text-destructive">
                  {defaultValueParsed.error}
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <button
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => setShowParamsSchema((s) => !s)}
              >
                {showParamsSchema ? "Hide" : "Show"} parameters schema (optional)
              </button>
              {showParamsSchema ? (
                <>
                  <Textarea
                    className="font-mono text-xs"
                    rows={5}
                    value={paramsSchemaText}
                    onChange={(e) => setParamsSchemaText(e.target.value)}
                    placeholder='{"type": "object", "properties": {...}}'
                  />
                  {!paramsSchemaParsed.ok ? (
                    <p className="text-xs text-destructive">
                      {paramsSchemaParsed.error}
                    </p>
                  ) : null}
                </>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cohorts</CardTitle>
            <CardDescription>
              Distribute traffic across cohorts. Percentages must sum to 100.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CohortEditor rows={rows} onChange={setRows} />
            {!cohortCheck.valid ? (
              <p className="mt-2 text-xs text-destructive">
                {cohortCheck.reason}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/flags")}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={
              saveDisabled ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {createMutation.isPending || updateMutation.isPending
              ? "Saving…"
              : isNew
                ? "Create flag"
                : "Save changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}
