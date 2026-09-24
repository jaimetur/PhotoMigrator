# DashboardAnalytic Instructions

## Language

- Always respond to me in Spanish unless I explicitly request another language in the chat.
- All source code must be written in English, including:
  - variable and function names;
  - class and module names;
  - comments and docstrings;
  - UI labels and dialog messages;
  - log messages;
  - warnings and error messages;
  - configuration keys and other developer-facing text.

## Changelog

- When editing the changelog, always update the section for the current version of the tool.
- If a release contains `Breaking Changes`, that section must always be the first section immediately after the release date.
- Add new changelog entries as the last bullet of the appropriate section, such as `New Features`, `Enhancements`, `Bug Fixes`, or `Documentation`.
- Keep the changelog concise and describe the final state of the implementation rather than the sequence of intermediate changes.
- Within the same current/unreleased version, do not create multiple changelog bullets for incremental changes, fixes, or refinements to the same functionality.
- If an existing changelog bullet already describes the same functionality, update or rewrite that bullet so it reflects the final behavior.
- Do not add changelog entries for internal implementation changes that have no relevant user-facing or developer-facing impact.

## Documentation

- Whenever implementing or modifying a feature, review all documentation related to that feature.
- Update any documentation that is no longer accurate after the change.
- Documentation must describe the final supported behavior, not intermediate implementation attempts or temporary states.

## Import, Export, Transfers, Backup and Restore

- Preserve compatibility with existing supported formats unless a breaking change is explicitly requested.
- When modifying the behavior, consider both sides of the workflow and verify round-trip compatibility when applicable.
- Do not silently change column names, field meanings, identifiers, data types, file structure, or exported semantics.
- Whenever a new feature introduces persistent or user-configurable data that is reasonably transferable or exportable — such as templates, queries, vendor/operator mappings, or similar entities — integrate that data into the relevant import/export and transfer workflows, as well as backup and restore.
- When extending an existing exportable data model, verify whether the corresponding importers, exporters, transfer mechanisms, backup, and restore logic also need to be updated.
- New exportable data should not remain available only inside the local application state unless there is a deliberate and documented reason to exclude it from import/export, transfers, backup, or restore.
