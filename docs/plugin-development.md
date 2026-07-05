# Plugin Development

DICE job types are plugins. A plugin provides metadata and a default workflow template.

## Minimal Plugin Shape

```python
from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class ExampleJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "example",
            "Example",
            "Example plugin.",
            [WorkflowTriggerKind.MANUAL],
            [WorkflowActionKind.NOTIFY],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.MANUAL, [WorkflowActionKind.NOTIFY])
```

## Rules

- Do not put plugin-specific logic in the job manager.
- Keep blockchain-specific code in adapters or action handlers.
- Use `WorkflowSpec` for trigger, condition, and action composition.
- Validate plugin-specific requirements in the plugin.
- Never log secrets.

## Future Direction

Plugins should eventually expose a schema that the TUI can use to build dynamic forms.
