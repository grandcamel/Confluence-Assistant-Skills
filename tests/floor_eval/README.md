# Shared Knowledge Floor evaluation

The job, inventory, fake models and offline tests are maintained once in the
[JIRA plugin's tests/floor_eval directory](../../../JIRA-Assistant-Skills/tests/floor_eval/README.md).
Keep a sibling JIRA-Assistant-Skills checkout (or substitute its absolute
path below). Python 3.10+ is sufficient for the driver; real evaluation needs
host CLI logins, with no Jira/Confluence site access.

From the Confluence repository:

```bash
python3 ../JIRA-Assistant-Skills/tests/floor_eval/run_eval.py \
  --repo confluence \
  --output ../JIRA-Assistant-Skills/tests/floor_eval/runs/confluence-release
# Resume that exact run:
python3 ../JIRA-Assistant-Skills/tests/floor_eval/run_eval.py \
  --repo confluence \
  --output ../JIRA-Assistant-Skills/tests/floor_eval/runs/confluence-release --resume
```

The filter includes facts shared across both repositories when any citation
belongs to Confluence. Omit `--repo` and use a separate output directory to
establish the required full 153-fact baseline. The checked-in inventory carries
source excerpts; the sibling Confluence checkout is needed for citation
re-auditing, not for model execution.

Run before every plugin release and after floor-model/judge changes in the
organization's `docs/agents/standing/fleet-posture.json`, updating the shared
`commands.json` for the new models. The release checklist is in the
[repository README](../../README.md#before-each-plugin-release). This is a
manual host-triggered check, never a model job in GitHub Actions. All raw
responses, recovery receipts and reports live under the chosen output path;
archive them and review disagreements/source issues/stale candidates before
using the classifications. Fake runs prove only the plumbing.
