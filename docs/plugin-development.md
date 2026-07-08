# Plugin Development

DICE job types are plugins. A plugin provides metadata, TUI form hints, and a default workflow
template.

## Minimal Plugin Shape

```python
from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


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
            [
                field("trigger_kind", "Trigger", "trigger", "manual"),
                field("function_name", "Action", "execution", "notify"),
            ],
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
- Expose plugin-specific field hints through `metadata(..., form_fields)`.
- Never log secrets.

## Form Field Hints

Form field hints are dictionaries created with `dice.jobs.templates.field`.

```python
field(
    key="contract_address",
    label="Contract address",
    step="contract",
    placeholder="0xTargetContract",
    required=True,
)
```

Current wizard steps that can use hints:

```text
wallet
asset
contract
trigger
execution
```

The TUI uses these hints to change copy and placeholders per job type. The job manager still uses
normal `JobConfig` validation and plugin validation before saving.

## Action Handlers

Workflow actions are executed through `dice.execution.actions`. Built-in handlers exist for:

```text
call_contract
transfer_native
transfer_erc20
wait
notify
withdraw
sweep
```

New plugins should prefer composing these actions before adding new action kinds. If a plugin needs
a new action kind, add a handler to `WorkflowActionDispatcher` and keep chain-specific transaction
building inside adapters.
